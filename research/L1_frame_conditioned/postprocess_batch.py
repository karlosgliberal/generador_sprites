"""Batch post-process existing raw frames: remove bg + normalize + rescale."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

from .postprocess import normalize_frames, remove_black_bg

OUTPUT_DIR = Path(__file__).parent.parent.parent / "research_output"


def process_action(run_dir: Path, target_size: int = 256) -> Path:
    """Post-process a single action's raw frames."""
    # Load frames
    frame_files = sorted(run_dir.glob("frame_*.png"))
    if not frame_files:
        print(f"  No frames in {run_dir}")
        return run_dir

    frames = [Image.open(f) for f in frame_files]
    print(f"  Loaded {len(frames)} frames from {run_dir.name}")

    # Step 1: Remove black background
    frames_transparent = [remove_black_bg(f) for f in frames]

    # Step 2: Normalize (union bbox + center + rescale)
    normalized = normalize_frames(frames_transparent, target_size=target_size, padding_pct=0.05)

    # Save to subdirectory
    out_dir = run_dir / f"processed_{target_size}"
    out_dir.mkdir(exist_ok=True)

    for i, frame in enumerate(normalized):
        frame.save(out_dir / f"frame_{i:02d}.png")

    # Strip
    if normalized:
        w, h = normalized[0].size
        strip = Image.new("RGBA", (w * len(normalized), h), (0, 0, 0, 0))
        for i, frame in enumerate(normalized):
            strip.paste(frame, (w * i, 0))
        strip.save(out_dir / "strip.png")

    # GIF (composite on black for visibility)
    if normalized:
        gif_frames = []
        for f in normalized:
            bg = Image.new("RGBA", f.size, (0, 0, 0, 255))
            bg.paste(f, mask=f.split()[3])
            gif_frames.append(bg.convert("RGB"))
        gif_frames[0].save(
            out_dir / "animation.gif",
            save_all=True,
            append_images=gif_frames[1:],
            duration=150,
            loop=0,
        )

    print(f"  Saved to {out_dir}")
    return out_dir


def main():
    target_size = int(sys.argv[1]) if len(sys.argv) > 1 else 256

    # Find the latest L1.3b runs
    run_dirs = sorted(OUTPUT_DIR.glob("L1.3b_*"))
    if not run_dirs:
        print("No L1.3b runs found")
        return

    for run_dir in run_dirs:
        if run_dir.is_dir():
            print(f"\nProcessing: {run_dir.name}")
            process_action(run_dir, target_size=target_size)


if __name__ == "__main__":
    main()
