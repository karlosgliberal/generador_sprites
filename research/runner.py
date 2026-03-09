"""CLI runner for research lines.

Usage:
    python -m generador_sprites.research --line L1 --action idle
    python -m generador_sprites.research --line L1 --action idle --subfase L1.1-gemini-direct
    python -m generador_sprites.research --line L1 --test smoke
    python -m generador_sprites.research --compare L1 L2 --action idle
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .fixtures import (
    DEFAULT_DESCRIPTION,
    SMOKE_TEST_ACTIONS,
    STANDARD_TEST_ACTIONS,
    TEST_CHARACTERS,
)

OUTPUT_DIR = Path(__file__).parent.parent / "research_output"


def get_research_line(line_id: str):
    """Import and instantiate a research line by ID."""
    registry = {}

    # Each line registers itself when its module exists
    if line_id == "L1":
        try:
            from .L1_frame_conditioned import FrameConditionedLine
            return FrameConditionedLine()
        except ImportError as e:
            print(f"Error loading L1: {e}")
            sys.exit(1)

    available = list(registry.keys()) or ["L1 (when implemented)"]
    print(f"Unknown line: {line_id}. Available: {available}")
    sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    """Run a single research experiment."""
    line = get_research_line(args.line)
    description = args.description or DEFAULT_DESCRIPTION
    character = args.character

    if character and character in TEST_CHARACTERS:
        description = TEST_CHARACTERS[character]

    print(f"Research line: {line.name} ({line.line_id})")
    print(f"Action: {args.action}")
    print(f"Description: {description[:80]}...")
    print()

    result = line.run(
        description=description,
        action=args.action,
        subfase=args.subfase or "",
        output_dir=OUTPUT_DIR,
    )

    if result.errors:
        print(f"\nErrors: {result.errors}")
    else:
        print(f"\nSuccess: {len(result.frames)} frames in {result.metadata.get('elapsed_seconds', '?')}s")


def cmd_test(args: argparse.Namespace) -> None:
    """Run standard test suite for a line."""
    line = get_research_line(args.line)
    actions = SMOKE_TEST_ACTIONS if args.level == "smoke" else STANDARD_TEST_ACTIONS
    description = DEFAULT_DESCRIPTION

    print(f"Testing {line.name} ({line.line_id})")
    print(f"Level: {args.level} ({len(actions)} actions)")
    print()

    results = []
    for action in actions:
        print(f"--- {action} ---")
        result = line.run(
            description=description,
            action=action,
            subfase=f"{line.line_id}-test-{args.level}",
            output_dir=OUTPUT_DIR,
        )
        results.append(result)
        status = "OK" if not result.errors else f"FAIL: {result.errors[0]}"
        print(f"  {status} ({len(result.frames)} frames)\n")

    passed = sum(1 for r in results if not r.errors)
    print(f"\nResults: {passed}/{len(results)} passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Research line runner")
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run a single experiment")
    p_run.add_argument("--line", required=True, help="Research line (L1, L2, ...)")
    p_run.add_argument("--action", required=True, help="Animation action")
    p_run.add_argument("--description", default=None, help="Avatar description")
    p_run.add_argument("--character", default=None, help="Named test character")
    p_run.add_argument("--subfase", default="", help="Subfase identifier")

    # test
    p_test = sub.add_parser("test", help="Run test suite for a line")
    p_test.add_argument("--line", required=True, help="Research line (L1, L2, ...)")
    p_test.add_argument("--level", choices=["smoke", "standard", "full"], default="smoke")

    args = parser.parse_args()
    {"run": cmd_run, "test": cmd_test}[args.command](args)


if __name__ == "__main__":
    main()
