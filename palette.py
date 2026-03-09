"""Color palette for color-coded stickman templates.

Each body part uses 2 tones (light/dark). Classification uses nearest-neighbor
in RGB space with a max distance threshold to reject background/unknown pixels.
"""

from __future__ import annotations

import math
from typing import Optional

from PIL import Image
from pathlib import Path

HEAD = "head"
TORSO = "torso"
FRONT_ARM = "front_arm"
BACK_ARM = "back_arm"
FRONT_LEG = "front_leg"
BACK_LEG = "back_leg"

PART_NAMES = [HEAD, TORSO, FRONT_ARM, BACK_ARM, FRONT_LEG, BACK_LEG]

PALETTE: dict[tuple[int, int, int], str] = {
    (95, 205, 228): HEAD,
    (153, 229, 80): TORSO,
    (106, 190, 48): TORSO,
    (251, 242, 54): FRONT_ARM,
    (209, 204, 96): FRONT_ARM,
    (223, 113, 38): BACK_ARM,
    (179, 91, 32): BACK_ARM,
    (206, 80, 80): FRONT_LEG,
    (172, 50, 50): FRONT_LEG,
    (175, 26, 178): BACK_LEG,
    (149, 23, 153): BACK_LEG,
}

MAX_COLOR_DISTANCE = 30.0


def _color_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def classify_pixel(r: int, g: int, b: int) -> Optional[str]:
    """Classify an RGB pixel to a body part name, or None if background."""
    rgb = (r, g, b)
    if rgb in PALETTE:
        return PALETTE[rgb]
    best_dist = MAX_COLOR_DISTANCE
    best_part = None
    for ref_color, part in PALETTE.items():
        d = _color_distance(rgb, ref_color)
        if d < best_dist:
            best_dist = d
            best_part = part
    return best_part


def extract_palette(frame_path: str | Path) -> dict[str, list[tuple[int, int, int]]]:
    """Discover unique colors per body part from a template frame."""
    img = Image.open(frame_path).convert("RGBA")
    result: dict[str, list[tuple[int, int, int]]] = {p: [] for p in PART_NAMES}
    seen: set[tuple[int, int, int]] = set()
    for r, g, b, a in img.getdata():
        if a < 128:
            continue
        rgb = (r, g, b)
        if rgb in seen:
            continue
        seen.add(rgb)
        part = classify_pixel(r, g, b)
        if part and rgb not in result[part]:
            result[part].append(rgb)
    return result
