"""Shared Flux Kontext API client."""

from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

import requests

from .config import BFL_API_URL, ENV_PATH


def load_api_key(env_path: Path | None = None) -> str:
    """Read BFL_API_KEY from .env file."""
    return _load_env_key("BFL_API_KEY", env_path)


def load_gemini_key(env_path: Path | None = None) -> str:
    """Read GEMINI_API_KEY from .env file."""
    return _load_env_key("GEMINI_API_KEY", env_path)


def _load_env_key(key_name: str, env_path: Path | None = None) -> str:
    """Read a key from the .env file."""
    path = env_path or ENV_PATH
    if not path.exists():
        print(f"Error: {path} not found. Create it with {key_name}=your_key")
        sys.exit(1)
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key_name}="):
            value = line.split("=", 1)[1].strip()
            if "your_" in value and "_here" in value:
                break
            return value
    print(f"Error: {key_name} not set in {path}")
    sys.exit(1)


def image_to_base64(path: Path) -> str:
    """Encode an image file to base64 string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate_image(
    api_key: str,
    prompt: str,
    input_image_b64: str,
    model: str = "pro",
    seed: int | None = None,
) -> bytes:
    """Submit a Flux Kontext generation request, poll until ready, return image bytes."""
    endpoint = f"{BFL_API_URL}/flux-kontext-{model}"
    headers = {"x-key": api_key, "Content-Type": "application/json"}

    payload = {
        "prompt": prompt,
        "input_image": input_image_b64,
        "aspect_ratio": "1:1",
        "output_format": "png",
    }
    if seed is not None:
        payload["seed"] = seed

    resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    polling_url = result.get("polling_url")
    if not polling_url:
        task_id = result.get("id")
        if task_id:
            polling_url = f"{BFL_API_URL}/get_result?id={task_id}"
        else:
            raise RuntimeError(f"Unexpected API response: {result}")

    while True:
        time.sleep(0.5)
        poll_resp = requests.get(polling_url, headers=headers, timeout=30)
        poll_resp.raise_for_status()
        poll_data = poll_resp.json()

        status = poll_data.get("status")
        if status == "Ready":
            image_url = poll_data["result"]["sample"]
            return download_image(image_url)
        elif status in ("Error", "Failed"):
            raise RuntimeError(f"Generation failed: {poll_data}")


def download_image(url: str) -> bytes:
    """Download image from URL and return raw bytes."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content
