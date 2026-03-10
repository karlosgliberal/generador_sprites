"""Character presets and frame counts for sprite generation."""

from __future__ import annotations

TEST_CHARACTERS = {
    "ninja": "dark ninja, purple robes, glowing green eyes, retro 16-bit pixel art style",
    "knight": "paladin in silver armor, blue tabard, golden emblem, medieval fantasy, pixel art style",
    "cat": "shadow cat ninja, black fur, bright yellow eyes, red scarf, pixel art style",
    "monk": "shaolin monk, orange robes, shaved head, prayer beads around neck, bare feet, muscular arms, retro 16-bit pixel art style",
    "rabbit": "wizard rabbit, white fur, tall pointy blue hat with stars, long blue robe, wooden magic staff in hand, big ears poking through hat, retro 16-bit pixel art style",
}

FRAME_COUNTS = {
    "idle": 10,
    "walk": 8,
    "run": 8,
    "jump": 6,
    "punch": 8,
    "sword_attack": 6,
    "death": 10,
}

DEFAULT_ACTIONS = ["idle", "walk", "run", "jump", "punch", "death"]
