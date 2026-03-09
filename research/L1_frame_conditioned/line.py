"""L1 research line: frame-a-frame conditioned generation."""

from __future__ import annotations

from PIL import Image

from ..base import ResearchLine
from ..fixtures import FRAME_COUNTS, get_template_frames


class FrameConditionedLine(ResearchLine):
    """Generate each animation frame by conditioning on avatar + pose template."""

    def __init__(self, subfase: str = "L1.1"):
        self._subfase = subfase
        self._subfase_impl = {
            "L1.1": self._subfase_1_gemini_direct,
            "L1.2": self._subfase_2_prompt_engineering,
        }

    @property
    def line_id(self) -> str:
        return "L1"

    @property
    def name(self) -> str:
        return "Frame-a-frame conditioned"

    def generate_frames(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        subfase: str | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        subfase = subfase or self._subfase
        impl = self._subfase_impl.get(subfase)
        if not impl:
            raise ValueError(f"Unknown subfase: {subfase}. Available: {list(self._subfase_impl.keys())}")
        return impl(description, action, num_frames, **kwargs)

    def _subfase_1_gemini_direct(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        """L1.1: Gemini direct - avatar reference + template as pose guide.

        For each template frame:
        1. Generate an avatar image from description (or reuse if provided)
        2. Pass avatar + template frame to Gemini with pose-following prompt
        3. Collect generated frame
        """
        from providers.factory import create_provider
        from .prompts import build_avatar_prompt, build_frame_prompt

        provider = create_provider("gemini")
        templates = get_template_frames(action)
        target_frames = num_frames or len(templates)
        templates = templates[:target_frames]

        # Step 1: Generate base avatar (idle pose, neutral)
        avatar = kwargs.get("avatar")
        if avatar is None:
            avatar_prompt = build_avatar_prompt(description)
            idle_ref = get_template_frames("idle")[0]
            print(f"  Generating base avatar...")
            avatar = provider.generate(avatar_prompt, idle_ref)
            avatar = avatar.convert("RGBA")

        # Step 2: For each template frame, generate conditioned frame
        frames = []
        for i, template in enumerate(templates):
            prompt = build_frame_prompt(description, action, i, len(templates))
            print(f"  Frame {i+1}/{len(templates)}: generating...")
            frame = provider.generate(
                prompt,
                template,
                reference_images=[avatar],
            )
            frames.append(frame.convert("RGBA"))

        return frames

    def _subfase_2_prompt_engineering(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        """L1.2: Prompt engineering - optimized instructions for pose adherence.

        Will be implemented after evaluating L1.1 results.
        """
        raise NotImplementedError("L1.2 will be implemented after L1.1 evaluation")
