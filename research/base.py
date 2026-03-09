"""Base class for research lines.

Every research line implements the same contract:
  INPUT:  avatar description (text) + action name (string)
  OUTPUT: list of PIL Images (frames) + sprite strip

This ensures all lines are comparable and testable with the same fixtures.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image


@dataclass
class ResearchResult:
    """Output of a single research run."""

    line: str  # e.g. "L1", "L2"
    subfase: str  # e.g. "L1.1-gemini-direct"
    action: str  # e.g. "idle", "run"
    description: str  # avatar description used
    frames: list[Image.Image]  # generated frames
    strip: Optional[Image.Image] = None  # assembled strip
    metadata: dict = field(default_factory=dict)  # timing, cost, model, etc.
    errors: list[str] = field(default_factory=list)

    def save(self, output_dir: Path) -> Path:
        """Save result to disk with metadata for later comparison."""
        run_id = f"{self.subfase}_{self.action}_{int(time.time())}"
        run_dir = output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save individual frames
        for i, frame in enumerate(self.frames):
            frame.save(run_dir / f"frame_{i:02d}.png")

        # Assemble and save strip
        if self.frames:
            w, h = self.frames[0].size
            strip = Image.new("RGBA", (w * len(self.frames), h), (0, 0, 0, 0))
            for i, frame in enumerate(self.frames):
                strip.paste(frame, (w * i, 0))
            strip.save(run_dir / "strip.png")
            self.strip = strip

        # Save metadata
        meta = {
            "line": self.line,
            "subfase": self.subfase,
            "action": self.action,
            "description": self.description,
            "num_frames": len(self.frames),
            "frame_size": list(self.frames[0].size) if self.frames else None,
            "errors": self.errors,
            **self.metadata,
        }
        (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

        return run_dir


class ResearchLine(ABC):
    """Base class for a research line.

    Subclasses implement generate_frames() with their specific approach.
    The framework handles input/output, saving, and comparison.
    """

    @property
    @abstractmethod
    def line_id(self) -> str:
        """Short identifier, e.g. 'L1'."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""
        ...

    @abstractmethod
    def generate_frames(
        self,
        description: str,
        action: str,
        num_frames: int | None = None,
        **kwargs,
    ) -> list[Image.Image]:
        """Generate animation frames for the given avatar + action.

        Args:
            description: Text description of the avatar
            action: Animation action (idle, walk, run, jump, punch, sword_attack, death)
            num_frames: Target number of frames (None = line decides)

        Returns:
            List of RGBA PIL Images
        """
        ...

    def run(
        self,
        description: str,
        action: str,
        subfase: str = "",
        output_dir: Path | None = None,
        **kwargs,
    ) -> ResearchResult:
        """Execute a research run with timing and error capture."""
        subfase = subfase or self.line_id
        t0 = time.time()
        errors = []
        frames = []

        try:
            frames = self.generate_frames(description, action, **kwargs)
        except Exception as e:
            errors.append(f"{type(e).__name__}: {e}")

        elapsed = time.time() - t0

        result = ResearchResult(
            line=self.line_id,
            subfase=subfase,
            action=action,
            description=description,
            frames=frames,
            errors=errors,
            metadata={"elapsed_seconds": round(elapsed, 2), **kwargs},
        )

        if output_dir:
            saved = result.save(output_dir)
            print(f"Result saved to {saved}")

        return result
