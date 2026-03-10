"""Core sprite generation pipeline (extracted from research L1.3b).

Main functions:
- generate_avatar(): Create base character image
- generate_action_frames(): Generate animation frames for an action
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image

from ..providers.base import ImageProvider
from ..providers.factory import create_provider
from ..research.fixtures import get_template_frames
from .characters import FRAME_COUNTS
from .postprocess import create_gif, create_strip, normalize_frames, remove_black_bg
from .prompts import build_avatar_prompt, build_frame_prompt


def generate_avatar(
    description: str,
    provider: ImageProvider | None = None,
) -> Image.Image:
    """Generate a base avatar image from a text description.

    Returns an RGBA image (~1024x1024 from Gemini).
    """
    if provider is None:
        provider = create_provider("gemini")

    prompt = build_avatar_prompt(description)
    # Use idle template frame as pose reference
    idle_ref = get_template_frames("idle")[0]
    print(f"  Generating base avatar...")
    avatar = provider.generate(prompt, idle_ref)
    return avatar.convert("RGBA")


def generate_action_frames(
    description: str,
    action: str,
    avatar: Image.Image,
    provider: ImageProvider | None = None,
    num_frames: int | None = None,
    on_frame: Callable[[int, int, Image.Image], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> list[Image.Image]:
    """Generate animation frames for a single action.

    Args:
        description: Character text description
        action: Action name (idle, walk, run, jump, punch, death, etc.)
        avatar: Pre-generated avatar image (from generate_avatar)
        provider: Image provider (defaults to Gemini)
        num_frames: Override frame count (defaults to FRAME_COUNTS)
        on_frame: Callback(frame_idx, total, frame_image) called after each frame
        cancel_check: Callable returning True to abort generation

    Returns:
        List of raw RGBA frames (before post-processing)
    """
    if provider is None:
        provider = create_provider("gemini")

    target_frames = num_frames or FRAME_COUNTS.get(action, 8)

    frames: list[Image.Image] = []
    for i in range(target_frames):
        if cancel_check and cancel_check():
            print(f"  Generation cancelled at frame {i}/{target_frames}")
            break

        prompt = build_frame_prompt(
            description, action, i, target_frames,
            is_first=i == 0,
        )

        ref_images = None
        if i == 0:
            ref_label = "anchor"
        elif i == 1:
            ref_images = [frames[0]]
            ref_label = "f0"
        else:
            ref_images = [frames[0], frames[i - 1]]
            ref_label = f"f0+f{i-1}"

        print(f"  Frame {i+1}/{target_frames}: refs={ref_label}...")
        frame = provider.generate(
            prompt, avatar, reference_images=ref_images,
        )
        frame = frame.convert("RGBA")
        frames.append(frame)

        if on_frame:
            on_frame(i, target_frames, frame)

    return frames


def process_frames(
    frames: list[Image.Image],
    target_size: int = 256,
) -> list[Image.Image]:
    """Post-process raw frames: remove background + normalize size."""
    cleaned = [remove_black_bg(f) for f in frames]
    return normalize_frames(cleaned, target_size=target_size)


def generate_full(
    description: str,
    action: str,
    avatar: Image.Image,
    provider: ImageProvider | None = None,
    output_dir: Path | None = None,
    on_frame: Callable[[int, int, Image.Image], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict:
    """Full pipeline: generate frames + post-process + save outputs.

    Returns dict with keys: frames, strip_path, gif_path
    """
    raw_frames = generate_action_frames(
        description, action, avatar, provider,
        on_frame=on_frame, cancel_check=cancel_check,
    )

    if not raw_frames:
        return {"frames": [], "strip_path": None, "gif_path": None}

    print(f"  Post-processing {len(raw_frames)} frames...")
    processed = process_frames(raw_frames)

    result = {"frames": processed, "strip_path": None, "gif_path": None}

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save individual frames
        for i, frame in enumerate(processed):
            frame.save(output_dir / f"frame_{i:02d}.png")

        # Save strip
        strip = create_strip(processed)
        strip_path = output_dir / "strip.png"
        strip.save(strip_path)
        result["strip_path"] = str(strip_path)
        print(f"  Strip saved: {strip_path}")

        # Save GIF
        gif_path = output_dir / "animation.gif"
        create_gif(processed, str(gif_path))
        result["gif_path"] = str(gif_path)
        print(f"  GIF saved: {gif_path}")

    return result
