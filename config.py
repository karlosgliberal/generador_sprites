"""Centralized configuration for the sprite generator pipeline."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent
TEMPLATES_DIR = ROOT / "templates"
ENV_PATH = ROOT / ".env"
OUTPUT_DIR = ROOT / "output"

BFL_API_URL = "https://api.bfl.ai/v1"
