"""L1: Frame-a-frame conditioned generation.

Instead of cutting parts from an avatar, we generate each animation frame
directly by passing the AI model:
  1. The avatar as identity reference
  2. The template frame as pose guide

The model generates a complete frame that matches the pose while preserving
the character's visual identity.
"""

from .line import FrameConditionedLine

__all__ = ["FrameConditionedLine"]
