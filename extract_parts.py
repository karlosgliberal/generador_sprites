"""Extract body parts from an AI-generated avatar using template masks.

Pipeline:
1. Remove background (flood-fill from edges)
2. Downscale to extract_size
3. Apply template masks to crop each body part

FIX vs puppet/: accepts template_img parameter instead of hardcoding REFERENCE_FRAME.
This allows correct mask extraction for any pose family (attack uses 64x64, others 48x48).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .config import BG_LUMINANCE_THRESHOLD
from .parse_template import segment_frame


def remove_background_threshold(img: Image.Image, threshold: int = BG_LUMINANCE_THRESHOLD) -> Image.Image:
    """Remove dark background via flood-fill from edges.

    Only removes dark pixels that are *connected to the image border*,
    preserving dark characters (e.g. a black cat) in the center.
    """
    from scipy.ndimage import label

    arr = np.array(img.convert("RGBA"))
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    dark_mask = lum < threshold

    labeled, _ = label(dark_mask)

    h, w = dark_mask.shape
    border_labels: set[int] = set()
    for edge in [labeled[0, :], labeled[-1, :], labeled[:, 0], labeled[:, -1]]:
        border_labels.update(edge[edge > 0])

    bg_mask = np.isin(labeled, list(border_labels))
    arr[bg_mask, 3] = 0
    return Image.fromarray(arr)


def remove_background(img: Image.Image, threshold: int = BG_LUMINANCE_THRESHOLD) -> Image.Image:
    """Remove background using rembg (U2Net) with flood-fill fallback."""
    try:
        from rembg import remove
        return remove(img)
    except Exception:
        return remove_background_threshold(img, threshold)


def extract_parts(
    character_img: Image.Image,
    output_dir: Path,
    template_img: Image.Image | None = None,
    extract_size: int = 384,
    dilate: int = 2,
) -> None:
    """Extract body parts from character image using template masks.

    Args:
        character_img: Full avatar image (any resolution).
        output_dir: Directory to save part PNGs.
        template_img: Template frame to use for masks. If None, uses idle/frame_00.
        extract_size: Resolution to extract at (default 384, must be multiple of template size).
        dilate: Mask dilation in template pixels.
    """
    from scipy.ndimage import binary_dilation

    if template_img is None:
        from .config import TEMPLATES_DIR
        template_img = Image.open(TEMPLATES_DIR / "idle" / "frame_00.png")

    template_w, template_h = template_img.size
    scale_factor = extract_size / template_w
    sf = int(scale_factor)

    # Adjust extract_size to be exact multiple of template size
    extract_size = sf * template_w

    # Remove background at full resolution first
    clean_img = remove_background(character_img)

    # Downscale with LANCZOS
    char_resized = clean_img.resize((extract_size, extract_size), Image.LANCZOS)
    char_resized_path = output_dir / f"_character_{extract_size}.png"
    char_resized.save(char_resized_path)
    print(f"Character at {extract_size}x{extract_size}: {char_resized_path}")

    # Parse template to get masks
    parts = segment_frame(template_img)
    print(f"Found {len(parts)} body parts in template {template_w}x{template_h} (scale {sf}x, dilate {dilate}px)")

    char_array = np.array(char_resized)

    for name, part_mask in parts.items():
        mask = part_mask.mask
        if dilate > 0:
            mask = binary_dilation(mask, iterations=dilate)

        # Scale mask with nearest-neighbor using np.kron
        mask_scaled = np.kron(mask, np.ones((sf, sf), dtype=bool))

        # Compute bbox from the dilated+scaled mask
        ys, xs = np.where(mask_scaled)
        if len(xs) == 0:
            continue
        sx0, sy0 = int(xs.min()), int(ys.min())
        sx1, sy1 = int(xs.max()) + 1, int(ys.max()) + 1
        bw, bh = sx1 - sx0, sy1 - sy0

        part_img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        part_array = np.array(part_img)

        mask_crop = mask_scaled[sy0:sy1, sx0:sx1]
        char_crop = char_array[sy0:sy1, sx0:sx1]

        part_array[mask_crop] = char_crop[mask_crop]

        part_img = Image.fromarray(part_array)
        part_path = output_dir / f"{name}.png"
        part_img.save(part_path)
        print(f"  {name}: {bw}x{bh}px, {int(mask_crop.sum())} pixels -> {part_path}")

    print(f"\nParts saved to {output_dir}/")
