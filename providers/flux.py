"""Flux Kontext Pro provider."""

from __future__ import annotations

import base64
from io import BytesIO

from PIL import Image

from ..flux_client import generate_image, load_api_key
from .base import ImageProvider


class FluxProvider(ImageProvider):
    def __init__(self, model: str = "pro", api_key: str | None = None):
        self.model = model
        self._api_key = api_key or load_api_key()

    def generate(
        self,
        prompt: str,
        input_image: Image.Image,
        seed: int | None = None,
        reference_images: list[Image.Image] | None = None,
    ) -> Image.Image:
        buf = BytesIO()
        input_image.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        img_data = generate_image(
            api_key=self._api_key,
            prompt=prompt,
            input_image_b64=img_b64,
            model=self.model,
            seed=seed,
        )
        return Image.open(BytesIO(img_data)).convert("RGBA")

    @property
    def name(self) -> str:
        return f"Flux Kontext {self.model.title()}"

    @property
    def cost_per_call(self) -> float:
        return 0.04 if self.model == "pro" else 0.08
