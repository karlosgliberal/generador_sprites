"""Abstract base for image generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from PIL import Image


class ImageProvider(ABC):
    """Interface for image generation backends (Flux, Gemini, PixelLab, SDXL, etc.)."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        input_image: Image.Image,
        seed: int | None = None,
        reference_images: list[Image.Image] | None = None,
    ) -> Image.Image:
        """Generate an image from a prompt and reference image(s)."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def cost_per_call(self) -> float:
        ...
