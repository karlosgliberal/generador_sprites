"""Shared test fixtures for all research lines.

All lines use the same inputs so results are directly comparable.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Standard test characters - same for all lines
TEST_CHARACTERS = {
    "ninja": "dark ninja, purple robes, glowing green eyes, retro 16-bit pixel art style",
    "knight": "paladin in silver armor, blue tabard, golden emblem, medieval fantasy, pixel art style",
    "cat": "shadow cat ninja, black fur, bright yellow eyes, red scarf, pixel art style",
}

# Default character for quick tests
DEFAULT_CHARACTER = "ninja"
DEFAULT_DESCRIPTION = TEST_CHARACTERS[DEFAULT_CHARACTER]

# Actions ordered by difficulty (simple → complex)
TEST_ACTIONS = ["idle", "walk", "run", "jump", "punch", "sword_attack", "death"]

# Quick smoke test: just idle (simplest)
SMOKE_TEST_ACTIONS = ["idle"]

# Standard test: covers the range without being exhaustive
STANDARD_TEST_ACTIONS = ["idle", "walk", "punch"]

# Frame counts per action (from templates)
FRAME_COUNTS = {
    "idle": 10,
    "walk": 8,
    "run": 8,
    "jump": 6,
    "punch": 8,
    "sword_attack": 6,
    "death": 10,
}

# Template sizes
TEMPLATE_SIZES = {
    "idle": (48, 48),
    "walk": (48, 48),
    "run": (48, 48),
    "jump": (48, 48),
    "punch": (64, 64),
    "sword_attack": (64, 64),
    "death": (48, 48),
}


def get_template_frames(action: str) -> list[Image.Image]:
    """Load all template frames for an action."""
    action_dir = TEMPLATES_DIR / action
    if not action_dir.exists():
        raise FileNotFoundError(f"Template not found: {action_dir}")
    frames = sorted(action_dir.glob("frame_*.png"))
    return [Image.open(f).convert("RGBA") for f in frames]


def get_reference_frame(action: str, frame_idx: int = 0) -> Image.Image:
    """Load a specific template frame."""
    path = TEMPLATES_DIR / action / f"frame_{frame_idx:02d}.png"
    if not path.exists():
        raise FileNotFoundError(f"Frame not found: {path}")
    return Image.open(path).convert("RGBA")
