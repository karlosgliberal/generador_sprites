"""Post-processing: background removal, normalization, pixelization."""

from __future__ import annotations

import numpy as np
from PIL import Image


def remove_black_bg(img: Image.Image, threshold: int = 30) -> Image.Image:
    """Replace near-black background with transparency."""
    arr = np.array(img.convert("RGBA"))
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    is_black = (r < threshold) & (g < threshold) & (b < threshold)
    arr[is_black, 3] = 0
    return Image.fromarray(arr)


def find_character_bbox(img: Image.Image, threshold: int = 10) -> tuple[int, int, int, int]:
    """Find bounding box of non-background content. Returns (x0, y0, x1, y1)."""
    arr = np.array(img.convert("RGBA"))
    alpha = arr[:, :, 3]
    mask = alpha > threshold

    if not mask.any():
        h, w = arr.shape[:2]
        return (0, 0, w, h)

    ys, xs = np.where(mask)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def normalize_frames(
    frames: list[Image.Image],
    target_size: int = 256,
    padding_pct: float = 0.1,
) -> list[Image.Image]:
    """Normalize all frames to consistent size and position via union bounding box."""
    if not frames:
        return frames

    all_x0, all_y0 = float("inf"), float("inf")
    all_x1, all_y1 = 0, 0

    for frame in frames:
        x0, y0, x1, y1 = find_character_bbox(frame)
        all_x0 = min(all_x0, x0)
        all_y0 = min(all_y0, y0)
        all_x1 = max(all_x1, x1)
        all_y1 = max(all_y1, y1)

    bbox_w = all_x1 - all_x0
    bbox_h = all_y1 - all_y0
    bbox_size = max(bbox_w, bbox_h)

    pad = int(bbox_size * padding_pct)
    bbox_size += pad * 2

    cx = (all_x0 + all_x1) // 2
    cy = (all_y0 + all_y1) // 2
    half = bbox_size // 2

    crop_x0 = cx - half
    crop_y0 = cy - half
    crop_x1 = crop_x0 + bbox_size
    crop_y1 = crop_y0 + bbox_size

    normalized = []
    for frame in frames:
        w, h = frame.size
        canvas = Image.new("RGBA", (w + bbox_size * 2, h + bbox_size * 2), (0, 0, 0, 0))
        offset_x = bbox_size
        offset_y = bbox_size
        canvas.paste(frame, (offset_x, offset_y))

        adj_x0 = crop_x0 + offset_x
        adj_y0 = crop_y0 + offset_y
        adj_x1 = crop_x1 + offset_x
        adj_y1 = crop_y1 + offset_y

        cropped = canvas.crop((adj_x0, adj_y0, adj_x1, adj_y1))
        resized = cropped.resize((target_size, target_size), Image.LANCZOS)
        normalized.append(resized)

    return normalized


def create_strip(frames: list[Image.Image]) -> Image.Image:
    """Concatenate frames into a horizontal sprite strip."""
    if not frames:
        raise ValueError("No frames to create strip from")
    w, h = frames[0].size
    strip = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        strip.paste(frame, (i * w, 0))
    return strip


def create_gif(frames: list[Image.Image], path: str, duration: int = 100) -> None:
    """Save frames as animated GIF."""
    if not frames:
        return
    gif_frames = []
    for f in frames:
        rgb = Image.new("RGBA", f.size, (0, 0, 0, 255))
        rgb.paste(f, mask=f.split()[3] if f.mode == "RGBA" else None)
        gif_frames.append(rgb.convert("RGB"))
    gif_frames[0].save(
        path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=duration,
        loop=0,
    )
