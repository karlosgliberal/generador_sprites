"""Action CRUD + generation trigger routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db, storage, tasks

router = APIRouter(prefix="/api", tags=["actions"])


class CreateActionRequest(BaseModel):
    action_name: str


class ActionResponse(BaseModel):
    id: str
    avatar_id: str
    action_name: str
    status: str
    frame_count: int | None
    strip_url: str | None
    gif_url: str | None
    created_at: str
    completed_at: str | None


class FrameResponse(BaseModel):
    id: str
    frame_index: int
    image_url: str


def _action_to_response(row: dict) -> ActionResponse:
    strip_url = storage.get_image_url(row["strip_path"]) if row.get("strip_path") else None
    gif_url = storage.get_image_url(row["gif_path"]) if row.get("gif_path") else None
    return ActionResponse(
        id=row["id"],
        avatar_id=row["avatar_id"],
        action_name=row["action_name"],
        status=row["status"],
        frame_count=row.get("frame_count"),
        strip_url=strip_url,
        gif_url=gif_url,
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


@router.post("/avatars/{avatar_id}/actions", response_model=ActionResponse)
def create_action(avatar_id: str, req: CreateActionRequest):
    avatar = db.query_one("SELECT * FROM avatars WHERE id = ?", (avatar_id,))
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")

    # Check if action already exists
    existing = db.query_one(
        "SELECT * FROM actions WHERE avatar_id = ? AND action_name = ?",
        (avatar_id, req.action_name),
    )
    if existing and existing["status"] in ("generating", "completed"):
        raise HTTPException(
            status_code=409,
            detail=f"Action '{req.action_name}' already exists (status: {existing['status']})",
        )

    # Delete previous failed/cancelled attempt if any
    if existing:
        db.execute("DELETE FROM frames WHERE action_id = ?", (existing["id"],))
        db.execute("DELETE FROM actions WHERE id = ?", (existing["id"],))
        storage.delete_action_files(avatar_id, req.action_name)

    action_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    db.execute(
        "INSERT INTO actions (id, avatar_id, action_name, status, created_at) VALUES (?, ?, ?, 'generating', ?)",
        (action_id, avatar_id, req.action_name, now),
    )

    # Load avatar image and start background generation
    avatar_img = storage.load_avatar_image(avatar_id)
    if not avatar_img:
        raise HTTPException(status_code=500, detail="Avatar image not found on disk")

    tasks.start_generation(
        action_id=action_id,
        avatar_id=avatar_id,
        action_name=req.action_name,
        description=avatar["description"],
        avatar_image=avatar_img,
    )

    row = db.query_one("SELECT * FROM actions WHERE id = ?", (action_id,))
    return _action_to_response(row)


@router.get("/avatars/{avatar_id}/actions", response_model=list[ActionResponse])
def list_actions(avatar_id: str):
    rows = db.query_all(
        "SELECT * FROM actions WHERE avatar_id = ? ORDER BY created_at",
        (avatar_id,),
    )
    return [_action_to_response(r) for r in rows]


@router.get("/actions/{action_id}", response_model=ActionResponse)
def get_action(action_id: str):
    row = db.query_one("SELECT * FROM actions WHERE id = ?", (action_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Action not found")
    return _action_to_response(row)


@router.get("/actions/{action_id}/frames", response_model=list[FrameResponse])
def get_action_frames(action_id: str):
    rows = db.query_all(
        "SELECT * FROM frames WHERE action_id = ? ORDER BY frame_index",
        (action_id,),
    )
    return [
        FrameResponse(
            id=r["id"],
            frame_index=r["frame_index"],
            image_url=storage.get_image_url(r["image_path"]),
        )
        for r in rows
    ]


@router.post("/actions/{action_id}/cancel")
def cancel_action(action_id: str):
    row = db.query_one("SELECT * FROM actions WHERE id = ?", (action_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Action not found")
    if row["status"] != "generating":
        raise HTTPException(status_code=400, detail="Action is not generating")

    tasks.cancel_generation(action_id)
    return {"ok": True}


@router.delete("/actions/{action_id}")
def delete_action(action_id: str):
    row = db.query_one("SELECT * FROM actions WHERE id = ?", (action_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Action not found")

    # Cancel if still generating
    if row["status"] == "generating":
        tasks.cancel_generation(action_id)

    db.execute("DELETE FROM frames WHERE action_id = ?", (action_id,))
    db.execute("DELETE FROM actions WHERE id = ?", (action_id,))
    storage.delete_action_files(row["avatar_id"], row["action_name"])

    return {"ok": True}
