"""Background generation tasks with cancellation support."""

from __future__ import annotations

import logging
import threading
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from PIL import Image

from ..pipeline.generator import generate_action_frames, process_frames
from ..pipeline.postprocess import create_gif, create_strip
from ..providers.factory import create_provider
from . import db, storage

logger = logging.getLogger(__name__)

# Active cancel events: action_id -> Event
_cancel_events: dict[str, threading.Event] = {}

# SSE subscribers: action_id -> list of queues
_subscribers: dict[str, list] = defaultdict(list)

# Lock for subscriber management
_sub_lock = threading.Lock()


def subscribe(action_id: str):
    """Create a new SSE subscriber queue for an action."""
    import queue
    q: queue.Queue = queue.Queue()
    with _sub_lock:
        _subscribers[action_id].append(q)
    return q


def unsubscribe(action_id: str, q) -> None:
    with _sub_lock:
        subs = _subscribers.get(action_id, [])
        if q in subs:
            subs.remove(q)
        if not subs and action_id in _subscribers:
            del _subscribers[action_id]


def _notify(action_id: str, event: str, data: dict) -> None:
    """Send event to all subscribers of an action."""
    import json
    with _sub_lock:
        subs = list(_subscribers.get(action_id, []))
    msg = {"event": event, **data}
    for q in subs:
        try:
            q.put_nowait(json.dumps(msg))
        except Exception:
            pass


def start_generation(
    action_id: str,
    avatar_id: str,
    action_name: str,
    description: str,
    avatar_image: Image.Image,
) -> None:
    """Launch generation in a background thread."""
    cancel_event = threading.Event()
    _cancel_events[action_id] = cancel_event

    thread = threading.Thread(
        target=_generation_worker,
        args=(action_id, avatar_id, action_name, description, avatar_image, cancel_event),
        daemon=True,
    )
    thread.start()


def cancel_generation(action_id: str) -> bool:
    """Signal cancellation for an active generation."""
    ev = _cancel_events.get(action_id)
    if ev:
        ev.set()
        return True
    return False


def is_generating(action_id: str) -> bool:
    return action_id in _cancel_events


def _generation_worker(
    action_id: str,
    avatar_id: str,
    action_name: str,
    description: str,
    avatar_image: Image.Image,
    cancel_event: threading.Event,
) -> None:
    """Worker thread: generates frames, saves to disk/DB, notifies SSE."""
    provider = create_provider("gemini")
    raw_frames: list[Image.Image] = []

    def on_frame(idx: int, total: int, frame: Image.Image) -> None:
        raw_frames_copy = list(raw_frames)  # not used here, frames tracked in outer list
        # Save raw frame temporarily
        frame_path = storage.save_frame(avatar_id, action_name, idx, frame)
        frame_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "INSERT INTO frames (id, action_id, frame_index, image_path, created_at) VALUES (?, ?, ?, ?, ?)",
            (frame_id, action_id, idx, frame_path, now),
        )
        db.execute(
            "UPDATE actions SET frame_count = ? WHERE id = ?",
            (idx + 1, action_id),
        )
        _notify(action_id, "frame_complete", {
            "frame_index": idx,
            "total_frames": total,
            "image_url": storage.get_image_url(frame_path),
        })

    def cancel_check() -> bool:
        return cancel_event.is_set()

    try:
        raw_frames = generate_action_frames(
            description=description,
            action=action_name,
            avatar=avatar_image,
            provider=provider,
            on_frame=on_frame,
            cancel_check=cancel_check,
        )

        if cancel_event.is_set():
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                "UPDATE actions SET status = 'cancelled', completed_at = ? WHERE id = ?",
                (now, action_id),
            )
            _notify(action_id, "cancelled", {"frame_count": len(raw_frames)})
            return

        # Post-processing
        _notify(action_id, "postprocessing", {"frame_count": len(raw_frames)})

        processed = process_frames(raw_frames)
        action_path = storage.action_dir(avatar_id, action_name)

        # Overwrite frames with processed versions
        for i, frame in enumerate(processed):
            storage.save_frame(avatar_id, action_name, i, frame)

        # Create strip
        strip = create_strip(processed)
        strip_path = storage.save_strip(avatar_id, action_name, strip)

        # Create GIF
        gif_path = str(action_path / "animation.gif")
        create_gif(processed, gif_path)

        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "UPDATE actions SET status = 'completed', frame_count = ?, strip_path = ?, gif_path = ?, completed_at = ? WHERE id = ?",
            (len(processed), strip_path, gif_path, now, action_id),
        )

        _notify(action_id, "completed", {
            "frame_count": len(processed),
            "strip_url": storage.get_image_url(strip_path),
            "gif_url": storage.get_image_url(gif_path),
        })

    except Exception as e:
        logger.exception(f"Generation failed for action {action_id}")
        now = datetime.now(timezone.utc).isoformat()
        db.execute(
            "UPDATE actions SET status = 'failed', completed_at = ? WHERE id = ?",
            (now, action_id),
        )
        _notify(action_id, "error", {"message": str(e)})

    finally:
        _cancel_events.pop(action_id, None)
