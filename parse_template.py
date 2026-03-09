"""Parse color-coded stickman templates into body part masks and joints."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw

from .palette import PART_NAMES, classify_pixel


@dataclass
class PartMask:
    name: str
    mask: np.ndarray  # bool array, same size as frame
    centroid: tuple[int, int]  # (x, y)
    bbox: tuple[int, int, int, int]  # (x0, y0, x1, y1)
    pixel_count: int


@dataclass
class Joint:
    part_a: str
    part_b: str
    position: tuple[int, int]  # (x, y) midpoint of boundary


@dataclass
class FrameParse:
    width: int
    height: int
    parts: dict[str, PartMask]
    joints: list[Joint]


def segment_frame(img: Image.Image) -> dict[str, PartMask]:
    """Segment a template frame by color into body part masks."""
    img_rgba = img.convert("RGBA")
    w, h = img_rgba.size
    pixels = np.array(img_rgba)

    masks: dict[str, np.ndarray] = {p: np.zeros((h, w), dtype=bool) for p in PART_NAMES}

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[y, x]
            if a < 128:
                continue
            part = classify_pixel(int(r), int(g), int(b))
            if part:
                masks[part][y, x] = True

    result = {}
    for name, mask in masks.items():
        count = int(mask.sum())
        if count == 0:
            continue
        ys, xs = np.where(mask)
        cx = int(xs.mean())
        cy = int(ys.mean())
        bbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        result[name] = PartMask(name=name, mask=mask, centroid=(cx, cy), bbox=bbox, pixel_count=count)

    return result


def find_joints(parts: dict[str, PartMask]) -> list[Joint]:
    """Find joints by boundary adjacency: dilate mask A by 1px, intersect with B."""
    from scipy.ndimage import binary_dilation

    joints = []
    part_names = list(parts.keys())

    for i, name_a in enumerate(part_names):
        dilated_a = binary_dilation(parts[name_a].mask, iterations=1)
        for name_b in part_names[i + 1 :]:
            overlap = dilated_a & parts[name_b].mask
            if overlap.any():
                ys, xs = np.where(overlap)
                jx = int(xs.mean())
                jy = int(ys.mean())
                joints.append(Joint(part_a=name_a, part_b=name_b, position=(jx, jy)))

    return joints


def parse_frame(img: Image.Image) -> FrameParse:
    """Parse a single template frame into parts and joints."""
    parts = segment_frame(img)
    joints = find_joints(parts)
    w, h = img.size
    return FrameParse(width=w, height=h, parts=parts, joints=joints)


def parse_animation(template_dir: str | Path) -> list[FrameParse]:
    """Parse all frames in a template directory."""
    template_dir = Path(template_dir)
    frames = sorted(template_dir.glob("frame_*.png"))
    return [parse_frame(Image.open(f)) for f in frames]


def compute_pivots(frame_parse: FrameParse) -> dict[str, tuple[int, int]]:
    """Compute pivot point for each part based on joints.

    Pivot = the joint connecting this part to torso (its "anchor" point).
    Falls back to centroid if no joint to torso is found.
    """
    pivots: dict[str, tuple[int, int]] = {}

    torso_joints: dict[str, tuple[int, int]] = {}
    for joint in frame_parse.joints:
        if joint.part_a == "torso":
            torso_joints[joint.part_b] = joint.position
        elif joint.part_b == "torso":
            torso_joints[joint.part_a] = joint.position

    for name, part in frame_parse.parts.items():
        if name == "torso":
            pivots[name] = part.centroid
        elif name in torso_joints:
            pivots[name] = torso_joints[name]
        else:
            pivots[name] = part.centroid

    return pivots


def compute_z_order(frame_parse: FrameParse) -> list[str]:
    """Compute dynamic z-order based on centroid X positions."""
    base_priority = {
        "back_arm": 0, "back_leg": 1, "torso": 2,
        "head": 3, "front_leg": 4, "front_arm": 5,
    }

    parts_with_priority = []
    for name, part in frame_parse.parts.items():
        bp = base_priority.get(name, 2)
        parts_with_priority.append((bp, part.centroid[0], name))

    parts_with_priority.sort()
    return [name for _, _, name in parts_with_priority]


def visualize_parse(img: Image.Image, frame_parse: FrameParse, scale: int = 8) -> Image.Image:
    """Create a debug visualization with colored overlays and joint markers."""
    PART_COLORS = {
        "head": (0, 200, 255, 128), "torso": (0, 255, 0, 128),
        "front_arm": (255, 255, 0, 128), "back_arm": (255, 140, 0, 128),
        "front_leg": (255, 50, 50, 128), "back_leg": (200, 0, 200, 128),
    }

    w, h = img.size
    out_w, out_h = w * scale, h * scale
    base = img.convert("RGBA").resize((out_w, out_h), Image.NEAREST)
    overlay = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))

    for name, part in frame_parse.parts.items():
        color = PART_COLORS.get(name, (128, 128, 128, 128))
        mask_scaled = np.kron(part.mask, np.ones((scale, scale), dtype=bool))
        ys, xs = np.where(mask_scaled)
        for y_px, x_px in zip(ys, xs):
            overlay.putpixel((int(x_px), int(y_px)), color)

    base = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(base)

    for name, part in frame_parse.parts.items():
        cx, cy = part.centroid[0] * scale, part.centroid[1] * scale
        r = max(2, scale // 2)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255))
        draw.text((cx + r + 2, cy - r), name, fill=(255, 255, 255, 255))

    for joint in frame_parse.joints:
        jx, jy = joint.position[0] * scale, joint.position[1] * scale
        r = max(3, scale // 2 + 1)
        draw.ellipse([jx - r, jy - r, jx + r, jy + r], fill=(255, 0, 0, 255), outline=(255, 255, 255, 255))

    return base
