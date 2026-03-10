"""CLI for the consolidated pipeline.

Usage (from inside the project directory):
    python pipeline/__main__.py --character ninja --actions "idle,walk,death"
    python pipeline/__main__.py --description "wizard cat" --actions "idle,punch"
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Ensure the parent directory is in sys.path so 'generador_sprites' is importable
# even when running from inside the project directory.
_project_parent = str(Path(__file__).resolve().parent.parent.parent)
if _project_parent not in sys.path:
    sys.path.insert(0, _project_parent)

from generador_sprites.pipeline.characters import FRAME_COUNTS, TEST_CHARACTERS
from generador_sprites.pipeline.generator import generate_avatar, generate_full
from generador_sprites.providers.factory import create_provider


OUTPUT_DIR = Path(__file__).parent.parent / "output"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprite generation pipeline")
    parser.add_argument("--character", default=None, help=f"Preset character: {', '.join(TEST_CHARACTERS)}")
    parser.add_argument("--description", default=None, help="Custom character description")
    parser.add_argument("--actions", required=True, help="Comma-separated actions (idle,walk,punch)")
    parser.add_argument("--output", default=None, help="Output directory")
    args = parser.parse_args()

    if args.character and args.character in TEST_CHARACTERS:
        description = TEST_CHARACTERS[args.character]
        char_name = args.character
    elif args.description:
        description = args.description
        char_name = "custom"
    else:
        parser.error("Provide --character or --description")
        return

    actions = [a.strip() for a in args.actions.split(",")]
    output_base = Path(args.output) if args.output else OUTPUT_DIR / char_name

    provider = create_provider("gemini")

    print(f"Character: {char_name}")
    print(f"Description: {description[:80]}...")
    print(f"Actions: {', '.join(actions)}")
    print(f"Output: {output_base}")
    print()

    # Generate shared avatar
    t_start = time.time()
    avatar = generate_avatar(description, provider)
    avatar_dir = output_base
    avatar_dir.mkdir(parents=True, exist_ok=True)
    avatar.save(avatar_dir / "avatar.png")
    print(f"  Avatar saved ({time.time() - t_start:.1f}s)\n")

    # Generate each action
    total_frames = sum(FRAME_COUNTS.get(a, 8) for a in actions)
    generated = 0

    for i, action in enumerate(actions):
        n_frames = FRAME_COUNTS.get(action, 8)
        print(f"{'='*50}")
        print(f"[{i+1}/{len(actions)}] {action.upper()} ({n_frames} frames)")
        print(f"{'='*50}")

        action_dir = output_base / action
        result = generate_full(
            description, action, avatar, provider,
            output_dir=action_dir,
        )

        generated += len(result["frames"])
        elapsed = time.time() - t_start
        avg = elapsed / generated if generated else 0
        remaining = (total_frames - generated) * avg
        print(f"  Done: {len(result['frames'])} frames | "
              f"Progress: {generated}/{total_frames} | "
              f"Elapsed: {elapsed:.0f}s | ETA: ~{remaining:.0f}s\n")

    elapsed_total = time.time() - t_start
    print(f"\n{'='*50}")
    print(f"COMPLETE: {generated} frames in {elapsed_total:.0f}s")
    print(f"Output: {output_base}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
