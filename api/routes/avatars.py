"""Avatar CRUD routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...pipeline.generator import generate_avatar
from ...providers.factory import create_provider
from .. import db, storage

router = APIRouter(prefix="/api/avatars", tags=["avatars"])


class CreateAvatarRequest(BaseModel):
    description: str
    character_name: str | None = None


class AvatarResponse(BaseModel):
    id: str
    description: str
    character_name: str | None
    avatar_image_url: str | None
    created_at: str
    action_count: int = 0


def _avatar_to_response(row: dict) -> AvatarResponse:
    image_url = None
    if row.get("avatar_image_path"):
        image_url = storage.get_image_url(row["avatar_image_path"])
    count = db.query_one(
        "SELECT COUNT(*) as c FROM actions WHERE avatar_id = ?", (row["id"],)
    )
    return AvatarResponse(
        id=row["id"],
        description=row["description"],
        character_name=row.get("character_name"),
        avatar_image_url=image_url,
        created_at=row["created_at"],
        action_count=count["c"] if count else 0,
    )


@router.post("", response_model=AvatarResponse)
def create_avatar(req: CreateAvatarRequest):
    avatar_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Check for character preset
    from ...pipeline.characters import TEST_CHARACTERS
    description = req.description
    if req.character_name and req.character_name in TEST_CHARACTERS:
        description = TEST_CHARACTERS[req.character_name]

    # Generate avatar image
    provider = create_provider("gemini")
    try:
        img = generate_avatar(description, provider)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Avatar generation failed: {e}")

    image_path = storage.save_avatar_image(avatar_id, img)

    db.execute(
        "INSERT INTO avatars (id, description, character_name, avatar_image_path, created_at) VALUES (?, ?, ?, ?, ?)",
        (avatar_id, description, req.character_name, image_path, now),
    )

    row = db.query_one("SELECT * FROM avatars WHERE id = ?", (avatar_id,))
    return _avatar_to_response(row)


@router.get("", response_model=list[AvatarResponse])
def list_avatars():
    rows = db.query_all("SELECT * FROM avatars ORDER BY created_at DESC")
    return [_avatar_to_response(r) for r in rows]


@router.get("/{avatar_id}", response_model=AvatarResponse)
def get_avatar(avatar_id: str):
    row = db.query_one("SELECT * FROM avatars WHERE id = ?", (avatar_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Avatar not found")
    return _avatar_to_response(row)


@router.delete("/{avatar_id}")
def delete_avatar(avatar_id: str):
    row = db.query_one("SELECT * FROM avatars WHERE id = ?", (avatar_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Avatar not found")

    # Cancel any active generations
    from .. import tasks
    active_actions = db.query_all(
        "SELECT id FROM actions WHERE avatar_id = ? AND status = 'generating'",
        (avatar_id,),
    )
    for action in active_actions:
        tasks.cancel_generation(action["id"])

    # Delete DB records (cascade) and files
    db.execute("DELETE FROM frames WHERE action_id IN (SELECT id FROM actions WHERE avatar_id = ?)", (avatar_id,))
    db.execute("DELETE FROM actions WHERE avatar_id = ?", (avatar_id,))
    db.execute("DELETE FROM avatars WHERE id = ?", (avatar_id,))
    storage.delete_avatar_files(avatar_id)

    return {"ok": True}
