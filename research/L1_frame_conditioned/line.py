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
            "L1.2a": self._subfase_2a_upscaled_template,
            "L1.2b": self._subfase_2b_swapped_order,
            "L1.2c": self._subfase_2c_text_only_pose,
            "L1.3": self._subfase_3_temporal_consistency,
            "L1.3b": self._subfase_3b_anchor_plus_prev,
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

    def _generate_avatar(self, description: str, provider) -> Image.Image:
        """Generate base avatar (shared across subfases)."""
        from .prompts import build_avatar_prompt

        avatar_prompt = build_avatar_prompt(description)
        idle_ref = get_template_frames("idle")[0]
        print(f"  Generating base avatar...")
        avatar = provider.generate(avatar_prompt, idle_ref)
        return avatar.convert("RGBA")

    def _subfase_1_gemini_direct(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        """L1.1: Gemini direct - baseline (template ignored by model)."""
        from generador_sprites.providers.factory import create_provider
        from .prompts import build_frame_prompt

        provider = create_provider("gemini")
        templates = get_template_frames(action)
        target_frames = num_frames or len(templates)
        templates = templates[:target_frames]

        avatar = kwargs.get("avatar") or self._generate_avatar(description, provider)

        frames = []
        for i, template in enumerate(templates):
            prompt = build_frame_prompt(description, action, i, len(templates))
            print(f"  Frame {i+1}/{len(templates)}: generating...")
            frame = provider.generate(prompt, template, reference_images=[avatar])
            frames.append(frame.convert("RGBA"))

        return frames

    def _subfase_2a_upscaled_template(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        """L1.2a: Upscale template to 512x512 + explicit color mapping in prompt.

        Hypothesis: 48x48 template is too small for Gemini to interpret.
        Upscaling with NEAREST preserves the color blocks as visible regions.
        """
        from generador_sprites.providers.factory import create_provider
        from .prompts import build_frame_prompt_v2a

        provider = create_provider("gemini")
        templates = get_template_frames(action)
        target_frames = num_frames or len(templates)
        templates = templates[:target_frames]

        avatar = kwargs.get("avatar") or self._generate_avatar(description, provider)

        frames = []
        for i, template in enumerate(templates):
            # Upscale template so Gemini can actually see the pose
            template_big = template.resize((512, 512), Image.NEAREST)

            prompt = build_frame_prompt_v2a(description, action, i, len(templates))
            print(f"  Frame {i+1}/{len(templates)}: [2a] upscaled template...")
            frame = provider.generate(prompt, template_big, reference_images=[avatar])
            frames.append(frame.convert("RGBA"))

        return frames

    def _subfase_2b_swapped_order(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        """L1.2b: Swap image roles - template as reference, avatar as primary.

        Hypothesis: Gemini treats input_image (last in contents) as "the image
        to transform" and reference_images as supplementary. By making the
        avatar the input_image, Gemini may focus more on transforming it
        according to the template pose shown in reference_images.
        """
        from generador_sprites.providers.factory import create_provider
        from .prompts import build_frame_prompt_v2b

        provider = create_provider("gemini")
        templates = get_template_frames(action)
        target_frames = num_frames or len(templates)
        templates = templates[:target_frames]

        avatar = kwargs.get("avatar") or self._generate_avatar(description, provider)

        frames = []
        for i, template in enumerate(templates):
            template_big = template.resize((512, 512), Image.NEAREST)

            prompt = build_frame_prompt_v2b(description, action, i, len(templates))
            print(f"  Frame {i+1}/{len(templates)}: [2b] swapped order...")
            # SWAP: avatar is input_image, template is reference
            frame = provider.generate(prompt, avatar, reference_images=[template_big])
            frames.append(frame.convert("RGBA"))

        return frames

    def _subfase_2c_text_only_pose(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        """L1.2c: Text-only pose description, no template image.

        Hypothesis: the template image confuses the model. Describe the pose
        entirely in text and only use the avatar as visual reference.
        """
        from generador_sprites.providers.factory import create_provider
        from .prompts import build_frame_prompt_v2c

        provider = create_provider("gemini")
        templates = get_template_frames(action)
        target_frames = num_frames or len(templates)

        avatar = kwargs.get("avatar") or self._generate_avatar(description, provider)

        frames = []
        for i in range(target_frames):
            prompt = build_frame_prompt_v2c(description, action, i, target_frames)
            print(f"  Frame {i+1}/{target_frames}: [2c] text-only pose...")
            # Only avatar, no template image
            frame = provider.generate(prompt, avatar)
            frames.append(frame.convert("RGBA"))

        return frames

    def _subfase_3_temporal_consistency(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        """L1.3: Temporal consistency via chained frame references.

        Builds on L1.2c (text-only pose, winner strategy). For each frame:
        - Avatar is always the primary input (identity anchor)
        - Previous frames are passed as reference_images (consistency anchor)
        - Prompt explicitly instructs to match size/position/style of prev frames

        Uses a sliding window of max 3 previous frames to avoid overloading
        the model's context while maintaining temporal coherence.
        """
        from generador_sprites.providers.factory import create_provider
        from .prompts import build_frame_prompt_v3

        provider = create_provider("gemini")
        templates = get_template_frames(action)
        target_frames = num_frames or len(templates)
        max_ref_frames = int(kwargs.get("max_ref_frames", 3))

        avatar = kwargs.get("avatar") or self._generate_avatar(description, provider)

        frames = []
        for i in range(target_frames):
            has_prev = len(frames) > 0
            prompt = build_frame_prompt_v3(
                description, action, i, target_frames, has_prev_frames=has_prev,
            )

            # Build reference chain: avatar + last N generated frames
            ref_images = []
            if frames:
                # Sliding window: keep last max_ref_frames
                recent = frames[-max_ref_frames:]
                ref_images = recent

            print(f"  Frame {i+1}/{target_frames}: [L1.3] refs={len(ref_images)} prev frames...")
            frame = provider.generate(
                prompt, avatar, reference_images=ref_images if ref_images else None,
            )
            frames.append(frame.convert("RGBA"))

        return frames

    def _subfase_3b_anchor_plus_prev(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        """L1.3b: Anchor frame + only last frame as reference.

        Fix for L1.3's inertia problem: instead of a sliding window of 3
        frames (which locks the model into repeating the same pose), use:
        - Frame 0 as identity/style anchor (always present)
        - Only the immediately previous frame for temporal continuity

        This gives the model a stable identity reference while allowing
        pose to evolve frame-to-frame without accumulating inertia.
        """
        from generador_sprites.providers.factory import create_provider
        from .prompts import build_frame_prompt_v3b

        provider = create_provider("gemini")
        templates = get_template_frames(action)
        target_frames = num_frames or len(templates)

        avatar = kwargs.get("avatar") or self._generate_avatar(description, provider)

        frames = []
        for i in range(target_frames):
            prompt = build_frame_prompt_v3b(
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

            print(f"  Frame {i+1}/{target_frames}: [L1.3b] refs={ref_label}...")
            frame = provider.generate(
                prompt, avatar, reference_images=ref_images,
            )
            frames.append(frame.convert("RGBA"))

        return frames
