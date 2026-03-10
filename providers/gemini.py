"""Gemini Flash provider for image generation with retry on transient errors."""

from __future__ import annotations

import logging
import time

from PIL import Image

from ..flux_client import load_gemini_key
from .base import ImageProvider

logger = logging.getLogger(__name__)

RETRY_STATUS_CODES = (429, 503)
MAX_RETRIES = 4
BASE_DELAY = 2  # seconds, doubles each retry: 2, 4, 8, 16


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

        config = types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        )

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = self._get_client().models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )

                if response.candidates:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data is not None:
                            from io import BytesIO
                            img = Image.open(BytesIO(part.inline_data.data))
                            return img.convert("RGBA")

                text = getattr(response, "text", "") or ""
                raise RuntimeError(f"Gemini returned no image. Response: {text[:300]}")

            except Exception as e:
                last_error = e
                status_code = getattr(e, "status_code", None) or getattr(e, "code", None)
                # Also check string representation for HTTP status codes
                error_str = str(e)
                is_retryable = (
                    status_code in RETRY_STATUS_CODES
                    or "503" in error_str
                    or "429" in error_str
                    or "RESOURCE_EXHAUSTED" in error_str
                    or "UNAVAILABLE" in error_str
                )

                if is_retryable and attempt < MAX_RETRIES:
                    delay = BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Gemini error (attempt {attempt + 1}/{MAX_RETRIES + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    print(f"    ⚠ Gemini {status_code or 'error'}, retrying in {delay}s...")
                    time.sleep(delay)
                    continue

                raise

        raise last_error  # type: ignore[misc]

    @property
    def name(self) -> str:
        short = self.model.replace("gemini-", "").replace("-preview-image-generation", "")
        return f"Gemini {short}"

    @property
    def cost_per_call(self) -> float:
        return 0.04
