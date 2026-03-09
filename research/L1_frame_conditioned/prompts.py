"""Prompt templates for L1: frame-conditioned generation.

Separated from logic so they can be iterated independently (L1.2).
"""

from __future__ import annotations


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
    """Build prompt for generating a single animation frame.

    The key insight: the template frame IS the pose guide. We tell the model
    to transform it into the character while keeping the exact pose.
    """
    action_descriptions = {
        "idle": "standing idle, slight breathing motion",
        "walk": "walking cycle",
        "run": "running cycle",
        "jump": "jumping motion",
        "punch": "punching attack",
        "sword_attack": "sword slash attack",
        "death": "death/collapse animation",
    }

    action_desc = action_descriptions.get(action, action)
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
