"""Renderer: compose character parts onto canvas using parsed pose data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from .palette import BACK_ARM, BACK_LEG, FRONT_ARM, FRONT_LEG, HEAD, TORSO
from .parse_template import FrameParse, compute_pivots, compute_z_order

DRAW_ORDER = [BACK_ARM, BACK_LEG, TORSO, HEAD, FRONT_LEG, FRONT_ARM]

PLACEHOLDER_COLORS = {
    HEAD: (0, 180, 220, 255), TORSO: (50, 180, 50, 255),
    FRONT_ARM: (220, 220, 30, 255), BACK_ARM: (200, 120, 30, 255),
    FRONT_LEG: (200, 50, 50, 255), BACK_LEG: (160, 30, 160, 255),
}

PLACEHOLDER_SIZES = {
    HEAD: (8, 8), TORSO: (8, 10),
    FRONT_ARM: (4, 10), BACK_ARM: (4, 10),
    FRONT_LEG: (4, 10), BACK_LEG: (4, 10),
}

JOINT_OVERLAP = {
    FRONT_ARM: 4, BACK_ARM: 4,
    FRONT_LEG: 3, BACK_LEG: 3,
    HEAD: 2,
}


@dataclass
class CharacterParts:
    """Collection of body part images for a character."""

    parts: dict[str, Image.Image]
    pivots: dict[str, tuple[int, int]] = field(default_factory=dict)

    @classmethod
    def create_placeholder(cls) -> CharacterParts:
        parts = {}
        for name in DRAW_ORDER:
            w, h = PLACEHOLDER_SIZES[name]
            parts[name] = Image.new("RGBA", (w, h), PLACEHOLDER_COLORS[name])
        return cls(parts=parts)

    @classmethod
    def load(cls, parts_dir: str | Path) -> CharacterParts:
        """Load character parts from PNG files in a directory."""
        parts_dir = Path(parts_dir)
        parts = {}
        pivots = {}

        for name in DRAW_ORDER:
            path = parts_dir / f"{name}.png"
            if path.exists():
                try:
                    parts[name] = Image.open(path).convert("RGBA")
                except Exception:
                    print(f"  Warning: corrupt {path}, using placeholder")
                    w, h = PLACEHOLDER_SIZES[name]
                    parts[name] = Image.new("RGBA", (w, h), PLACEHOLDER_COLORS[name])
            else:
                w, h = PLACEHOLDER_SIZES[name]
                parts[name] = Image.new("RGBA", (w, h), PLACEHOLDER_COLORS[name])

        manifest_path = parts_dir.parent / "character.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
                family_name = parts_dir.name
                if family_name in manifest.get("families", {}):
                    family_data = manifest["families"][family_name]
                    for pname, pdata in family_data.get("parts", {}).items():
                        if "pivot" in pdata:
                            pivots[pname] = tuple(pdata["pivot"])
            except (json.JSONDecodeError, KeyError):
                pass

        return cls(parts=parts, pivots=pivots)

    @classmethod
    def load_for_animation(cls, parts_dir: Path, animation: str) -> CharacterParts:
        """Load parts from the correct pose family for this animation."""
        from .pose_families import family_for_animation
        family = family_for_animation(animation)
        family_dir = parts_dir / family
        if family_dir.exists() and (family_dir / "head.png").exists():
            return cls.load(family_dir)
        return cls.load(parts_dir)


def feather_edges(img: Image.Image, radius: int = 2) -> Image.Image:
    """Apply alpha feathering to edges of a part image."""
    if radius <= 0:
        return img
    arr = np.array(img)
    if arr.shape[2] < 4:
        return img
    alpha = Image.fromarray(arr[:, :, 3])
    blurred = alpha.filter(ImageFilter.GaussianBlur(radius=radius))
    blurred_arr = np.array(blurred)
    arr[:, :, 3] = np.minimum(arr[:, :, 3], blurred_arr)
    return Image.fromarray(arr)


def render_frame(
    char_parts: CharacterParts,
    frame_parse: FrameParse,
    output_size: int = 96,
    feather: int = 0,
    use_pivots: bool = True,
    use_dynamic_z: bool = True,
) -> Image.Image:
    """Render a single frame by placing character parts at parsed positions."""
    canvas = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))
    scale = output_size / frame_parse.width

    template_pivots = compute_pivots(frame_parse) if use_pivots else {}
    draw_order = compute_z_order(frame_parse) if use_dynamic_z else DRAW_ORDER

    for bone in draw_order:
        if bone not in frame_parse.parts or bone not in char_parts.parts:
            continue

        part_mask = frame_parse.parts[bone]
        part_img = char_parts.parts[bone]

        bx0, by0, bx1, by1 = part_mask.bbox
        target_w = max(1, int((bx1 - bx0) * scale))
        target_h = max(1, int((by1 - by0) * scale))

        overlap = JOINT_OVERLAP.get(bone, 0)
        target_w += overlap * 2
        target_h += overlap * 2

        resized = part_img.resize((target_w, target_h), Image.LANCZOS)

        if feather > 0:
            resized = feather_edges(resized, radius=feather)

        if use_pivots and bone in template_pivots:
            pivot = template_pivots[bone]
            px = int(pivot[0] * scale)
            py = int(pivot[1] * scale)

            if bone in char_parts.pivots:
                cp = char_parts.pivots[bone]
                orig_w, orig_h = part_img.size
                if orig_w > 0 and orig_h > 0:
                    cpx = int(cp[0] * target_w / orig_w)
                    cpy = int(cp[1] * target_h / orig_h)
                else:
                    cpx, cpy = target_w // 2, target_h // 2
                paste_x = px - cpx
                paste_y = py - cpy
            else:
                paste_x = px - target_w // 2
                paste_y = py - target_h // 2
        else:
            cx = int(part_mask.centroid[0] * scale)
            cy = int(part_mask.centroid[1] * scale)
            paste_x = cx - target_w // 2
            paste_y = cy - target_h // 2

        canvas.alpha_composite(resized, (paste_x, paste_y))

    return canvas
