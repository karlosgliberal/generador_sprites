"""Filesystem storage for avatar images and animation frames.

Layout:
    data/avatars/{avatar_id}/
        avatar.png
        {action_name}/
            frame_00.png ... frame_09.png
            strip.png
            animation.gif
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

DATA_DIR = Path(__file__).parent.parent / "data"
AVATARS_DIR = DATA_DIR / "avatars"


def avatar_dir(avatar_id: str) -> Path:
    d = AVATARS_DIR / avatar_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def action_dir(avatar_id: str, action_name: str) -> Path:
    d = AVATARS_DIR / avatar_id / action_name
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_avatar_image(avatar_id: str, img: Image.Image) -> str:
    path = avatar_dir(avatar_id) / "avatar.png"
    img.save(path)
    return str(path)


def save_frame(avatar_id: str, action_name: str, frame_idx: int, img: Image.Image) -> str:
    path = action_dir(avatar_id, action_name) / f"frame_{frame_idx:02d}.png"
    img.save(path)
    return str(path)


def save_strip(avatar_id: str, action_name: str, img: Image.Image) -> str:
    path = action_dir(avatar_id, action_name) / "strip.png"
    img.save(path)
    return str(path)


def save_gif(avatar_id: str, action_name: str, gif_path_src: str) -> str:
    """Save GIF (already created by postprocess.create_gif)."""
    return gif_path_src  # GIF is already saved in place by generator


def load_avatar_image(avatar_id: str) -> Image.Image | None:
    path = avatar_dir(avatar_id) / "avatar.png"
    if path.exists():
        return Image.open(path).convert("RGBA")
    return None


def delete_avatar_files(avatar_id: str) -> None:
    import shutil
    d = AVATARS_DIR / avatar_id
    if d.exists():
        shutil.rmtree(d)


def delete_action_files(avatar_id: str, action_name: str) -> None:
    import shutil
    d = AVATARS_DIR / avatar_id / action_name
    if d.exists():
        shutil.rmtree(d)


def get_image_url(file_path: str) -> str:
    """Convert absolute file path to API-serveable URL."""
    p = Path(file_path)
    try:
        rel = p.relative_to(DATA_DIR)
        return f"/api/files/{rel}"
    except ValueError:
        return f"/api/files/{p.name}"
