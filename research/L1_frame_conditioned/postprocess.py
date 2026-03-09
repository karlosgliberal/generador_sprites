"""Post-processing for L1.4: normalize and pixelize generated frames.

L1.4b: Normalize size/position across frames
L1.4c: Pixelize (downscale + palette reduction + grid alignment)
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def remove_black_bg(img: Image.Image, threshold: int = 30) -> Image.Image:
    """Replace near-black background with transparency.

    Pixels where R, G, B are all below threshold become transparent.
    """
    arr = np.array(img.convert("RGBA"))
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    is_black = (r < threshold) & (g < threshold) & (b < threshold)
    arr[is_black, 3] = 0
    return Image.fromarray(arr)


def find_character_bbox(img: Image.Image, threshold: int = 10) -> tuple[int, int, int, int]:
    """Find bounding box of non-background content.

    Returns (x0, y0, x1, y1) of the character region.
    """
    arr = np.array(img.convert("RGBA"))
    # Character = pixels with alpha > threshold
    alpha = arr[:, :, 3]
    mask = alpha > threshold

    if not mask.any():
        h, w = arr.shape[:2]
        return (0, 0, w, h)

    ys, xs = np.where(mask)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def normalize_frames(
    frames: list[Image.Image],
    target_size: int = 128,
    padding_pct: float = 0.1,
) -> list[Image.Image]:
    """Normalize all frames to consistent size and position.

    1. Find the union bounding box across ALL frames (consistent crop)
    2. Add padding
    3. Resize all to target_size x target_size

    This ensures the character stays the same size and position.
    """
    if not frames:
        return frames

    # Find union bbox across all frames
    all_x0, all_y0 = float("inf"), float("inf")
    all_x1, all_y1 = 0, 0

    for frame in frames:
        x0, y0, x1, y1 = find_character_bbox(frame)
        all_x0 = min(all_x0, x0)
        all_y0 = min(all_y0, y0)
        all_x1 = max(all_x1, x1)
        all_y1 = max(all_y1, y1)

    # Make it square (use the larger dimension)
    bbox_w = all_x1 - all_x0
    bbox_h = all_y1 - all_y0
    bbox_size = max(bbox_w, bbox_h)

    # Add padding
    pad = int(bbox_size * padding_pct)
    bbox_size += pad * 2

    # Center the bbox
    cx = (all_x0 + all_x1) // 2
    cy = (all_y0 + all_y1) // 2
    half = bbox_size // 2

    crop_x0 = cx - half
    crop_y0 = cy - half
    crop_x1 = crop_x0 + bbox_size
    crop_y1 = crop_y0 + bbox_size

    # Crop and resize each frame
    normalized = []
    for frame in frames:
        w, h = frame.size
        # Create a canvas large enough to handle negative crops
        canvas = Image.new("RGBA", (w + bbox_size * 2, h + bbox_size * 2), (0, 0, 0, 0))
        offset_x = bbox_size
        offset_y = bbox_size
        canvas.paste(frame, (offset_x, offset_y))

        # Crop with offset
        adj_x0 = crop_x0 + offset_x
        adj_y0 = crop_y0 + offset_y
        adj_x1 = crop_x1 + offset_x
        adj_y1 = crop_y1 + offset_y

        cropped = canvas.crop((adj_x0, adj_y0, adj_x1, adj_y1))
        resized = cropped.resize((target_size, target_size), Image.LANCZOS)
        normalized.append(resized)

    return normalized


def pixelize(
    img: Image.Image,
    pixel_size: int = 4,
    num_colors: int = 32,
) -> Image.Image:
    """Convert a frame to clean pixel art.

    1. Downscale to pixel grid (target_size / pixel_size)
    2. Quantize to limited palette
    3. Upscale back with NEAREST (crisp pixels)
    """
    w, h = img.size
    small_w = w // pixel_size
    small_h = h // pixel_size

    # Downscale with LANCZOS (good averaging)
    small = img.resize((small_w, small_h), Image.LANCZOS)

    # Quantize palette
    # Convert to RGBA, quantize RGB, reapply alpha
    rgb = small.convert("RGB")
    quantized_rgb = rgb.quantize(colors=num_colors, method=Image.Quantize.MEDIANCUT)
    quantized_rgb = quantized_rgb.convert("RGB")

    # Reapply alpha from the small version
    small_arr = np.array(small.convert("RGBA"))
    quant_arr = np.array(quantized_rgb)
    result_arr = np.zeros((*quant_arr.shape[:2], 4), dtype=np.uint8)
    result_arr[:, :, :3] = quant_arr
    result_arr[:, :, 3] = small_arr[:, :, 3]

    # Threshold alpha: fully transparent or fully opaque
    result_arr[:, :, 3] = np.where(result_arr[:, :, 3] > 128, 255, 0)

    small_pixel = Image.fromarray(result_arr)

    # Upscale with NEAREST for crisp pixel art look
    return small_pixel.resize((w, h), Image.NEAREST)


def pixelize_frames(
    frames: list[Image.Image],
    pixel_size: int = 4,
    num_colors: int = 32,
) -> list[Image.Image]:
    """Apply pixelization to all frames with a shared palette.

    Uses the first frame to establish the palette, then applies it
    to all frames for color consistency.
    """
    if not frames:
        return frames

    # For now, pixelize each frame independently
    # TODO: shared palette extraction across all frames
    return [pixelize(f, pixel_size=pixel_size, num_colors=num_colors) for f in frames]
