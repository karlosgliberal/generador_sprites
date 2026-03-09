"""Shared utilities for the sprite generator pipeline."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def assemble_strip(frames: list[Image.Image], output_path: Path | None = None) -> Image.Image:
    """Assemble frames into a horizontal strip PNG."""
    if not frames:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    w, h = frames[0].size
    strip = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        strip.paste(frame, (w * i, 0))
    if output_path:
        strip.save(output_path)
        print(f"  Strip: {output_path} ({len(frames)} frames, {w}x{h} each)")
    return strip
