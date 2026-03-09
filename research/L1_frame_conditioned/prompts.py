"""Prompt templates for L1: frame-conditioned generation.

L1.1: Basic prompts (template ignored by model)
L1.2: Three strategies to force pose adherence:
  A) Upscale template + explicit color-to-part mapping
  B) Swap image order (avatar as reference, template as primary input)
  C) Describe pose in text, skip template image entirely  ← WINNER
L1.3: Temporal consistency - chain previous frames as reference
"""

from __future__ import annotations


# -- L1.1 prompts (kept for reference) --

def build_avatar_prompt(description: str) -> str:
    """Build prompt for initial avatar generation."""
    return (
        f"Create a pixel art game character sprite: {description}. "
        "Side view facing right, full body visible, centered. "
        "Retro 16-bit fighting game style. "
        "PURE SOLID BLACK BACKGROUND #000000. "
        "Keep the exact same pose and proportions as the reference template."
    )


def build_frame_prompt(
    description: str,
    action: str,
    frame_idx: int,
    total_frames: int,
) -> str:
    """L1.1 frame prompt (baseline)."""
    action_desc = ACTION_DESCRIPTIONS.get(action, action)
    progress = f"frame {frame_idx + 1} of {total_frames}"

    return (
        f"Transform this color-coded pose template into a pixel art game sprite. "
        f"The character is: {description}. "
        f"This is {progress} of a {action_desc} animation. "
        f"CRITICAL: Keep the EXACT same pose, proportions and body position as the template. "
        f"The colored regions show where each body part should be. "
        f"Replace each colored region with the corresponding part of the character. "
        f"Use the reference image to maintain the character's visual identity. "
        f"Retro 16-bit pixel art style. PURE SOLID BLACK BACKGROUND #000000. "
        f"Side view facing right."
    )


# -- L1.2 prompts --

ACTION_DESCRIPTIONS = {
    "idle": "standing idle, slight breathing motion",
    "walk": "walking cycle",
    "run": "running cycle",
    "jump": "jumping motion",
    "punch": "punching attack, arm extended forward",
    "sword_attack": "sword slash attack",
    "death": "death/collapse animation, falling to ground",
}

# Detailed pose descriptions per action per frame (key frames only)
POSE_DESCRIPTIONS = {
    "idle": {
        0: "standing upright, arms relaxed at sides, weight centered",
        3: "standing upright, slight lean back, chest expanded (breathing in)",
        6: "standing upright, slight lean forward, chest compressed (breathing out)",
    },
    "walk": {
        0: "left foot forward, right foot back, left arm back, right arm forward",
        2: "feet together, passing position, arms at sides",
        4: "right foot forward, left foot back, right arm back, left arm forward",
        6: "feet together, passing position, arms at sides",
    },
    "run": {
        0: "right leg extended far back, left knee high, arms pumping",
        2: "airborne, both feet off ground, legs switching",
        4: "left leg extended far back, right knee high, arms pumping",
        6: "airborne, both feet off ground, legs switching",
    },
    "jump": {
        0: "crouching, knees bent, arms back, preparing to jump",
        2: "mid-air, body extended upward, arms raised",
        4: "peak of jump, body fully extended",
        5: "descending, knees starting to bend for landing",
    },
    "punch": {
        0: "standing in fighting stance, fists raised",
        2: "pulling right arm back, body rotating",
        4: "right arm fully extended forward in punch, body leaning forward",
        6: "arm retracting, returning to stance",
    },
    "sword_attack": {
        0: "sword raised above head, both hands on hilt",
        2: "sword mid-swing, diagonal slash",
        4: "sword fully extended forward, end of slash",
        5: "returning to guard position",
    },
    "death": {
        0: "standing, hit by impact, leaning back",
        3: "falling backward, arms flailing",
        6: "almost horizontal, about to hit ground",
        9: "lying flat on ground, defeated, completely horizontal",
    },
}


def get_pose_description(action: str, frame_idx: int, total_frames: int) -> str:
    """Get a text description of the pose for a specific frame."""
    poses = POSE_DESCRIPTIONS.get(action, {})

    # Exact match
    if frame_idx in poses:
        return poses[frame_idx]

    # Interpolate between nearest described frames
    keys = sorted(poses.keys())
    if not keys:
        return ACTION_DESCRIPTIONS.get(action, action)

    if frame_idx <= keys[0]:
        return poses[keys[0]]
    if frame_idx >= keys[-1]:
        return poses[keys[-1]]

    # Find surrounding keyframes
    for i, k in enumerate(keys[:-1]):
        if k <= frame_idx < keys[i + 1]:
            prev_pose = poses[k]
            next_pose = poses[keys[i + 1]]
            t = (frame_idx - k) / (keys[i + 1] - k)
            if t < 0.5:
                return f"transitioning from: {prev_pose}"
            else:
                return f"transitioning into: {next_pose}"

    return ACTION_DESCRIPTIONS.get(action, action)


def build_frame_prompt_v2a(
    description: str,
    action: str,
    frame_idx: int,
    total_frames: int,
) -> str:
    """L1.2 Strategy A: Upscaled template with explicit color mapping.

    The template is upscaled before being passed. This prompt explains
    what each color means so the model understands the pose structure.
    """
    action_desc = ACTION_DESCRIPTIONS.get(action, action)
    pose_desc = get_pose_description(action, frame_idx, total_frames)

    return (
        f"I'm showing you TWO images:\n"
        f"1. A REFERENCE CHARACTER (pixel art sprite) - copy this character's visual style and identity\n"
        f"2. A COLOR-CODED POSE TEMPLATE - this shows the exact pose the character must be in\n\n"
        f"The pose template uses these colors for body parts:\n"
        f"- CYAN/light blue = head\n"
        f"- GREEN = torso/body\n"
        f"- YELLOW = front arm\n"
        f"- ORANGE = back arm\n"
        f"- RED = front leg\n"
        f"- PURPLE/magenta = back leg\n\n"
        f"Generate a pixel art sprite of: {description}\n"
        f"The pose is: {pose_desc}\n"
        f"This is frame {frame_idx + 1}/{total_frames} of a {action_desc} animation.\n\n"
        f"CRITICAL RULES:\n"
        f"- The character MUST match the EXACT pose shown in the color template\n"
        f"- Each colored region tells you where that body part goes\n"
        f"- Copy the character's appearance from the reference image\n"
        f"- Retro 16-bit pixel art style\n"
        f"- PURE SOLID BLACK BACKGROUND #000000\n"
        f"- Side view facing right"
    )


def build_frame_prompt_v2b(
    description: str,
    action: str,
    frame_idx: int,
    total_frames: int,
) -> str:
    """L1.2 Strategy B: Template as primary image, avatar as reference.

    Swap the role: the template is the main input to transform,
    and the avatar is supplementary reference for style.
    """
    action_desc = ACTION_DESCRIPTIONS.get(action, action)
    pose_desc = get_pose_description(action, frame_idx, total_frames)

    return (
        f"Transform this color-coded stickman into a detailed pixel art character.\n\n"
        f"The stickman shows the EXACT pose: {pose_desc}\n"
        f"Each color = a body part (cyan=head, green=torso, yellow=front arm, "
        f"orange=back arm, red=front leg, purple=back leg).\n\n"
        f"Replace each colored region with the matching body part of this character: {description}\n"
        f"The reference image shows what the character looks like - match its style, colors, and details.\n\n"
        f"Frame {frame_idx + 1}/{total_frames} of {action_desc}.\n"
        f"Keep the EXACT pose from the stickman. Pixel art, black background, side view right."
    )


def build_frame_prompt_v2c(
    description: str,
    action: str,
    frame_idx: int,
    total_frames: int,
) -> str:
    """L1.2 Strategy C: Text-only pose description, no template image.

    Skip the template entirely. Describe the pose in words and use
    only the avatar as visual reference for identity.
    """
    action_desc = ACTION_DESCRIPTIONS.get(action, action)
    pose_desc = get_pose_description(action, frame_idx, total_frames)

    return (
        f"Generate a pixel art sprite matching the reference character's appearance.\n"
        f"The character is: {description}\n\n"
        f"POSE for this frame: {pose_desc}\n"
        f"This is frame {frame_idx + 1}/{total_frames} of a {action_desc} animation.\n\n"
        f"The character MUST be in the described pose - this is different from the reference pose.\n"
        f"Keep the same character design, colors, proportions and style as the reference.\n"
        f"Retro 16-bit pixel art. PURE BLACK BACKGROUND #000000. Side view facing right."
    )


# -- L1.3 prompts: temporal consistency --

def build_frame_prompt_v3(
    description: str,
    action: str,
    frame_idx: int,
    total_frames: int,
    has_prev_frames: bool = False,
) -> str:
    """L1.3: Text pose + chained references for temporal consistency.

    Builds on L1.2c (text-only pose) but adds explicit instructions to
    maintain consistency with previous frames passed as reference images.
    """
    action_desc = ACTION_DESCRIPTIONS.get(action, action)
    pose_desc = get_pose_description(action, frame_idx, total_frames)

    ref_instructions = ""
    if has_prev_frames:
        ref_instructions = (
            "I'm showing you reference images:\n"
            "- FIRST image: the character's base design (identity reference)\n"
            "- FOLLOWING images: previously generated frames of this same animation\n\n"
            "You MUST maintain EXACTLY:\n"
            "- Same character size and proportions as the previous frames\n"
            "- Same vertical position (feet at same height)\n"
            "- Same art style, color palette, and level of detail\n"
            "- Same clothing/equipment - do NOT add or remove any items\n\n"
        )
    else:
        ref_instructions = (
            "The reference image shows the character's base design.\n\n"
        )

    return (
        f"{ref_instructions}"
        f"Generate frame {frame_idx + 1} of {total_frames} for a {action_desc} animation.\n"
        f"Character: {description}\n\n"
        f"POSE for this frame: {pose_desc}\n\n"
        f"RULES:\n"
        f"- Character MUST be in the described pose\n"
        f"- SAME character size, proportions, and position as reference frames\n"
        f"- SAME outfit and equipment - nothing added, nothing removed\n"
        f"- Retro 16-bit pixel art style\n"
        f"- PURE SOLID BLACK BACKGROUND #000000\n"
        f"- Side view facing right, centered in frame"
    )


def build_frame_prompt_v3b(
    description: str,
    action: str,
    frame_idx: int,
    total_frames: int,
    is_first: bool = False,
) -> str:
    """L1.3b: Anchor + previous frame only.

    Uses frame 0 as style/identity anchor and only the previous frame
    for temporal continuity. Avoids inertia from sliding window.
    Explicitly tells the model which frame shows what.
    """
    action_desc = ACTION_DESCRIPTIONS.get(action, action)
    pose_desc = get_pose_description(action, frame_idx, total_frames)

    if is_first:
        ref_instructions = (
            "The reference image shows the character's base design.\n"
            "Generate the FIRST frame of the animation.\n\n"
        )
    else:
        ref_instructions = (
            "I'm showing you reference images:\n"
            "- FIRST image: frame 1 of this animation (style/size anchor)\n"
            "- SECOND image: the previous frame in the sequence\n\n"
            "MATCH the exact same character size, position, and art style as these frames.\n"
            "Do NOT add or remove any clothing, weapons, or accessories.\n"
            "ONLY change the body POSE as described below.\n\n"
        )

    return (
        f"{ref_instructions}"
        f"Generate frame {frame_idx + 1} of {total_frames} for a {action_desc} animation.\n"
        f"Character: {description}\n\n"
        f"POSE for this frame: {pose_desc}\n\n"
        f"The pose MUST change from the previous frame to create fluid animation.\n"
        f"Retro 16-bit pixel art. PURE SOLID BLACK #000000 background. Side view facing right."
    )
