"""Unified CLI for the sprite generator.

Usage:
    python -m generador_sprites generate \
        --character shadow_ninja \
        --description "dark ninja, purple robes, green eyes" \
        --provider gemini \
        --seed 42

    python -m generador_sprites render \
        --parts parts/shadow_ninja_families \
        --animation idle \
        --output-size 96

    python -m generador_sprites extract \
        --from-image avatar.png \
        --template templates/idle/frame_00.png \
        --output parts/test
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate character families: 1 avatar per pose family + mask extraction."""
    from .config import PARTS_DIR, PROMPT_TEMPLATE, load_prompts, save_prompt
    from .providers.factory import create_provider
    from .generate_parts import generate_character_families
    from .pose_families import all_families

    provider = create_provider(args.provider)
    prompts = load_prompts()

    if args.character in prompts:
        prompt_text = prompts[args.character]
    else:
        prompt_text = PROMPT_TEMPLATE.format(description=args.description)
        save_prompt(args.character, args.description, prompt_text)

    output_dir = Path(args.output) if args.output else PARTS_DIR / f"{args.character}_families"

    print(f"Generating '{args.character}' with {provider.name}")
    print(f"  Families: {', '.join(all_families())}")
    print(f"  Cost: ~${provider.cost_per_call * len(all_families()):.2f}")
    print()

    generate_character_families(
        provider=provider,
        prompt_text=prompt_text,
        output_dir=output_dir,
        seed=args.seed,
        extract_size=args.extract_size,
    )

    print(f"\nDone! Parts in {output_dir}/")


def cmd_render(args: argparse.Namespace) -> None:
    """Render animation strip from extracted parts."""
    from .config import TEMPLATES_DIR
    from .renderer import CharacterParts, render_frame
    from .parse_template import parse_animation
    from .utils import assemble_strip

    parts_dir = Path(args.parts)
    parts = CharacterParts.load_for_animation(parts_dir, args.animation)

    template_dir = TEMPLATES_DIR / args.animation
    if not template_dir.exists():
        print(f"Error: template not found: {template_dir}")
        sys.exit(1)

    frame_parses = parse_animation(template_dir)
    print(f"Rendering '{args.animation}': {len(frame_parses)} frames at {args.output_size}x{args.output_size}")

    rendered = [render_frame(parts, fp, output_size=args.output_size) for fp in frame_parses]

    output_path = Path(args.output) if args.output else parts_dir / f"{args.animation}_strip.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    assemble_strip(rendered, output_path)


def cmd_extract(args: argparse.Namespace) -> None:
    """Extract parts from an existing avatar image."""
    from PIL import Image
    from .extract_parts import extract_parts

    avatar = Image.open(args.from_image).convert("RGBA")
    print(f"Loaded: {args.from_image} ({avatar.size[0]}x{avatar.size[1]})")

    template_img = None
    if args.template:
        template_img = Image.open(args.template)
        print(f"Template: {args.template} ({template_img.size[0]}x{template_img.size[1]})")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    extract_parts(avatar, output_dir, template_img=template_img, extract_size=args.extract_size)


def cmd_parse(args: argparse.Namespace) -> None:
    """Parse and visualize a template frame."""
    from PIL import Image
    from .parse_template import parse_frame, visualize_parse
    from .config import OUTPUT_DIR

    img = Image.open(args.frame)
    fp = parse_frame(img)

    print(f"Parse of {args.frame} ({fp.width}x{fp.height}):")
    for name, part in fp.parts.items():
        print(f"  {name}: centroid={part.centroid}, bbox={part.bbox}, pixels={part.pixel_count}")
    print(f"\nJoints ({len(fp.joints)}):")
    for j in fp.joints:
        print(f"  {j.part_a} <-> {j.part_b} at {j.position}")

    if args.viz:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        viz = visualize_parse(img, fp)
        viz_path = OUTPUT_DIR / f"parse_debug_{Path(args.frame).stem}.png"
        viz.save(viz_path)
        print(f"\nVisualization: {viz_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sprite generator: AI avatar + template-based part extraction")
    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    p_gen = sub.add_parser("generate", help="Generate character parts per pose family")
    p_gen.add_argument("--character", required=True, help="Character name (slug)")
    p_gen.add_argument("--description", required=True, help="Visual description")
    p_gen.add_argument("--seed", type=int, default=None)
    p_gen.add_argument("--provider", choices=["flux", "gemini"], default="flux")
    p_gen.add_argument("--extract-size", type=int, default=384)
    p_gen.add_argument("--output", default=None, help="Output dir (default: parts/<character>_families)")

    # render
    p_render = sub.add_parser("render", help="Render animation strip from parts")
    p_render.add_argument("--parts", required=True, help="Parts directory")
    p_render.add_argument("--animation", required=True, help="Animation name (idle, punch, etc.)")
    p_render.add_argument("--output-size", type=int, default=96)
    p_render.add_argument("--output", default=None, help="Output path for strip PNG")

    # extract
    p_ext = sub.add_parser("extract", help="Extract parts from existing avatar image")
    p_ext.add_argument("--from-image", required=True, help="Avatar image path")
    p_ext.add_argument("--template", default=None, help="Template frame for masks (default: idle/frame_00)")
    p_ext.add_argument("--output", required=True, help="Output directory for parts")
    p_ext.add_argument("--extract-size", type=int, default=384)

    # parse
    p_parse = sub.add_parser("parse", help="Parse and visualize a template frame")
    p_parse.add_argument("frame", help="Path to template frame PNG")
    p_parse.add_argument("--viz", action="store_true", help="Save debug visualization")

    args = parser.parse_args()

    commands = {
        "generate": cmd_generate,
        "render": cmd_render,
        "extract": cmd_extract,
        "parse": cmd_parse,
    }
    commands[args.command](args)
