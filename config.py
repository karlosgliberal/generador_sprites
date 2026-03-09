"""Centralized configuration for the sprite generator pipeline."""

from __future__ import annotations

import json
from pathlib import Path

# --- Paths (all relative to this package) ---
ROOT = Path(__file__).parent
TEMPLATES_DIR = ROOT / "templates"
ENV_PATH = ROOT / ".env"
OUTPUT_DIR = ROOT / "output"
PARTS_DIR = ROOT / "parts"

# --- Flux API ---
BFL_API_URL = "https://api.bfl.ai/v1"

# --- Template animation → game animation mapping ---
ANIMATION_MAP = {
    "idle": "idle",
    "punch": "attack",
    "death": "death",
    "walk": "walk",
    "run": "run",
    "jump": "jump",
    "sword_attack": "sword_attack",
}

# --- Character generation prompt template ---
PROMPTS_FILE = ROOT / "prompts.json"

PROMPT_TEMPLATE = (
    "Transform this color-coded pose template into a pixel art game sprite. "
    "{description}, retro 16-bit fighting game style. "
    "PURE SOLID BLACK BACKGROUND #000000. "
    "Keep the exact same pose and proportions. Side view facing right, full body visible."
)


def load_prompts() -> dict[str, str]:
    """Load prompts from JSON file. Returns {name: prompt_text}."""
    if not PROMPTS_FILE.exists():
        return {}
    data = json.loads(PROMPTS_FILE.read_text())
    return {k: v["prompt"] for k, v in data.items()}


def load_prompts_full() -> dict:
    """Load full prompts data (with descriptions) from JSON file."""
    if not PROMPTS_FILE.exists():
        return {}
    return json.loads(PROMPTS_FILE.read_text())


def save_prompt(name: str, description: str, prompt: str | None = None) -> None:
    """Save a new prompt to prompts.json. If no prompt given, build from template."""
    data = load_prompts_full()
    if prompt is None:
        prompt = PROMPT_TEMPLATE.format(description=description)
    data[name] = {"description": description, "prompt": prompt}
    PROMPTS_FILE.write_text(json.dumps(data, indent=2))


# --- Background removal ---
BG_LUMINANCE_THRESHOLD = 40
