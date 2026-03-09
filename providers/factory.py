"""Factory for creating image generation providers."""

from __future__ import annotations

from .base import ImageProvider


def create_provider(name: str = "flux", **kwargs) -> ImageProvider:
    """Create an image provider by name ("flux" or "gemini")."""
    if name == "gemini":
        from .gemini import GeminiProvider
        return GeminiProvider(**kwargs)
    from .flux import FluxProvider
    return FluxProvider(**kwargs)
