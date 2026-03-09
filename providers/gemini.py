"""Gemini Flash provider for image generation."""

from __future__ import annotations

from PIL import Image

from ..flux_client import load_gemini_key
from .base import ImageProvider


class GeminiProvider(ImageProvider):
    """Gemini via Google GenAI SDK. Supports multi-image reference_images."""

    def __init__(self, model: str = "gemini-2.5-flash-image", api_key: str | None = None):
        self.model = model
        self._api_key = api_key or load_gemini_key()
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.genai import Client
            self._client = Client(api_key=self._api_key)
        return self._client

    def generate(
        self,
        prompt: str,
        input_image: Image.Image,
        seed: int | None = None,
        reference_images: list[Image.Image] | None = None,
    ) -> Image.Image:
        from google.genai import types

        contents: list = [prompt]
        if reference_images:
            contents.extend(reference_images)
        contents.append(input_image)

        response = self._get_client().models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    from io import BytesIO
                    img = Image.open(BytesIO(part.inline_data.data))
                    return img.convert("RGBA")

        text = getattr(response, "text", "") or ""
        raise RuntimeError(f"Gemini returned no image. Response: {text[:300]}")

    @property
    def name(self) -> str:
        short = self.model.replace("gemini-", "").replace("-preview-image-generation", "")
        return f"Gemini {short}"

    @property
    def cost_per_call(self) -> float:
        return 0.04
