"""SSE endpoint for real-time generation progress."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from .. import db, storage, tasks

router = APIRouter(prefix="/api", tags=["generation"])


@router.get("/actions/{action_id}/progress")
async def action_progress(action_id: str):
    """SSE endpoint streaming generation progress.

    Events: frame_complete, postprocessing, completed, error, cancelled
    If action is already completed, sends all existing frames + completed.
    """
    action = db.query_one("SELECT * FROM actions WHERE id = ?", (action_id,))
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    return StreamingResponse(
        _sse_generator(action_id, action),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _sse_generator(action_id: str, action: dict):
    """Generate SSE events for an action."""
    # If already completed, send all existing frames then done
    if action["status"] in ("completed", "failed", "cancelled"):
        frames = db.query_all(
            "SELECT * FROM frames WHERE action_id = ? ORDER BY frame_index",
            (action_id,),
        )
        for f in frames:
            data = {
                "event": "frame_complete",
                "frame_index": f["frame_index"],
                "total_frames": action.get("frame_count") or len(frames),
                "image_url": storage.get_image_url(f["image_path"]),
            }
            yield f"data: {json.dumps(data)}\n\n"

        if action["status"] == "completed":
            data = {
                "event": "completed",
                "frame_count": action.get("frame_count") or len(frames),
            }
            if action.get("strip_path"):
                data["strip_url"] = storage.get_image_url(action["strip_path"])
            if action.get("gif_path"):
                data["gif_url"] = storage.get_image_url(action["gif_path"])
            yield f"data: {json.dumps(data)}\n\n"
        elif action["status"] == "failed":
            yield f"data: {json.dumps({'event': 'error', 'message': 'Generation failed'})}\n\n"
        elif action["status"] == "cancelled":
            yield f"data: {json.dumps({'event': 'cancelled', 'frame_count': len(frames)})}\n\n"
        return

    # Subscribe to live updates
    q = tasks.subscribe(action_id)
    try:
        while True:
            try:
                # Check queue with timeout to allow cancellation
                msg = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: q.get(timeout=1.0)
                )
                yield f"data: {msg}\n\n"

                # Check if this was a terminal event
                parsed = json.loads(msg)
                if parsed.get("event") in ("completed", "error", "cancelled"):
                    break

            except Exception:
                # Timeout - check if action is still active
                if not tasks.is_generating(action_id):
                    # Check final status
                    action = db.query_one("SELECT * FROM actions WHERE id = ?", (action_id,))
                    if action and action["status"] in ("completed", "failed", "cancelled"):
                        break
                continue
    finally:
        tasks.unsubscribe(action_id, q)
