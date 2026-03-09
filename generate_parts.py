"""Generate character parts per pose family via avatar + mask extraction.

For each pose family (neutral, attack, airborne, collapsed):
1. Generate 1 full avatar using the family's reference frame
2. Pass previous avatars as reference_images for consistency
3. Extract 6 body parts using THE SAME template as mask source
4. Compute pivots from template joints
5. Write character.json manifest

FIX vs puppet/: passes the correct template_img to extract_parts() for each family.
This ensures attack parts use attack masks (64x64), not idle masks (48x48).

Total cost: ~$0.16 per character (4 AI calls, one per family).
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from .config import TEMPLATES_DIR
from .extract_parts import extract_parts
from .parse_template import parse_frame, segment_frame
from .providers.base import ImageProvider
from .pose_families import POSE_FAMILIES, all_families


def generate_character_families(
    provider: ImageProvider,
    prompt_text: str,
    output_dir: Path,
    seed: int | None = None,
    families: list[str] | None = None,
    extract_size: int = 384,
    on_progress: callable | None = None,
) -> dict[str, dict[str, Path]]:
    """Generate parts for each pose family.

    Returns: {family_name: {part_name: path}}
    """
    families_to_gen = families or all_families()
    results: dict[str, dict[str, Path]] = {}
    total_steps = len(families_to_gen)
    step_idx = 0

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "name": output_dir.name,
        "prompt": prompt_text[:100],
        "seed": seed,
        "families": {},
    }

    neutral_avatar: Image.Image | None = None

    for family_name in families_to_gen:
        family_info = POSE_FAMILIES[family_name]
        ref_frame_path = TEMPLATES_DIR / family_info["reference_frame"]

        if not ref_frame_path.exists():
            print(f"  Warning: reference frame not found: {ref_frame_path}, skipping {family_name}")
            continue

        family_dir = output_dir / family_name
        family_dir.mkdir(parents=True, exist_ok=True)

        # Generate avatar for this family's pose
        step_idx += 1
        prompt_suffix = family_info.get("prompt_suffix", "")
        full_prompt = f"{prompt_text}, {prompt_suffix}" if prompt_suffix else prompt_text

        label = f"Generating {family_name} avatar"
        print(f"  [{step_idx}/{total_steps}] {label}...")
        if on_progress:
            on_progress(step_idx, total_steps, label)

        ref_image = Image.open(ref_frame_path).convert("RGBA")

        ref_images = [neutral_avatar] if (neutral_avatar is not None and family_name != "neutral") else None
        avatar = provider.generate(full_prompt, ref_image, seed=seed, reference_images=ref_images)
        avatar = avatar.convert("RGBA")

        if family_name == "neutral" or neutral_avatar is None:
            neutral_avatar = avatar

        avatar_path = output_dir / f"avatar_{family_name}.png"
        avatar.save(avatar_path)

        # Extract parts using THE SAME template that was used for generation
        # This is the key fix: attack family uses punch template (64x64), not idle (48x48)
        template_img = Image.open(ref_frame_path)
        print(f"         Extracting parts with {family_info['reference_frame']} masks ({template_img.size[0]}x{template_img.size[1]})...")
        extract_parts(avatar, family_dir, template_img=template_img, extract_size=extract_size)

        # Build manifest from template joints
        fp = parse_frame(template_img)
        parts_masks = segment_frame(template_img)

        family_parts: dict[str, Path] = {}
        family_manifest: dict = {"avatar": f"avatar_{family_name}.png", "parts": {}}

        for part_name, part_mask in parts_masks.items():
            part_path = family_dir / f"{part_name}.png"
            family_parts[part_name] = part_path

            pivot = list(part_mask.centroid)
            for joint in fp.joints:
                if part_name in (joint.part_a, joint.part_b):
                    other = joint.part_b if joint.part_a == part_name else joint.part_a
                    if other == "torso":
                        pivot = list(joint.position)
                        break

            family_manifest["parts"][part_name] = {
                "file": f"{family_name}/{part_name}.png",
                "pivot": pivot,
                "z_order": _z_order_for_part(part_name),
            }

        results[family_name] = family_parts
        manifest["families"][family_name] = family_manifest

    manifest_path = output_dir / "character.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  Manifest: {manifest_path}")

    return results


def _z_order_for_part(part_name: str) -> int:
    order = {
        "back_arm": 0, "back_leg": 1, "torso": 2,
        "head": 3, "front_leg": 4, "front_arm": 5,
    }
    return order.get(part_name, 2)
