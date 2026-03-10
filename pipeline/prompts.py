"""Prompt templates for sprite generation pipeline.

Based on L1.2c (text-only pose, no template) + L1.3b (anchor + prev frame).
"""

from __future__ import annotations

ACTION_DESCRIPTIONS = {
    "idle": "standing idle, slight breathing motion",
    "walk": "walking cycle",
    "run": "running cycle",
    "jump": "jumping motion",
    "punch": "punching attack, arm extended forward",
    "sword_attack": "sword slash attack",
    "death": "death/collapse animation, falling forward to ground",
}

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
        0: "crouching low, knees deeply bent, arms pulled back, preparing to leap",
        1: "pushing off ground, legs extending, arms swinging upward",
        2: "mid-air rising, legs tucked underneath, arms raised above head",
        3: "peak of jump, body fully stretched vertically, arms up high",
        4: "descending, legs extending downward, arms lowering to sides",
        5: "landing, knees bent absorbing impact, arms at sides for balance",
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
        0: "standing upright, just hit, flinching, head tilted back slightly",
        2: "stumbling forward, one hand on chest, knees starting to buckle",
        4: "dropping to knees, torso slumping forward, arms going limp",
        6: "on knees, upper body falling FORWARD toward the ground, NOT rotating or spinning sideways",
        8: "collapsed face-down on the ground, limbs spread, completely still",
        9: "lying face-down flat on the ground, motionless, defeated",
    },
}


def get_pose_description(action: str, frame_idx: int, total_frames: int) -> str:
    """Get a text description of the pose for a specific frame."""
    poses = POSE_DESCRIPTIONS.get(action, {})

    if frame_idx in poses:
        return poses[frame_idx]

    keys = sorted(poses.keys())
    if not keys:
        return ACTION_DESCRIPTIONS.get(action, action)

    if frame_idx <= keys[0]:
        return poses[keys[0]]
    if frame_idx >= keys[-1]:
        return poses[keys[-1]]

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
    is_first: bool = False,
) -> str:
    """Build prompt for a single animation frame (L1.3b strategy).

    Uses frame 0 as style/identity anchor + only previous frame for continuity.
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
            "The character's held items (staff, sword, weapon) MUST remain visible in every frame.\n"
            "ONLY change the body POSE as described below.\n\n"
        )

    death_extra = ""
    if action == "death":
        death_extra = (
            "IMPORTANT: The character is falling FORWARD, NOT rotating or spinning sideways. "
            "Keep the character grounded and natural.\n"
        )

    return (
        f"{ref_instructions}"
        f"Generate frame {frame_idx + 1} of {total_frames} for a {action_desc} animation.\n"
        f"Character: {description}\n\n"
        f"POSE for this frame: {pose_desc}\n\n"
        f"{death_extra}"
        f"The character's held items (staff, sword, weapon) MUST remain visible in every frame.\n"
        f"The pose MUST change from the previous frame to create fluid animation.\n"
        f"Retro 16-bit pixel art. PURE SOLID BLACK #000000 background. Side view facing right."
    )
