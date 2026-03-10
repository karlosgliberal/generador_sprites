"use client";

import { useEffect, useRef, useState } from "react";
import { cancelAction, subscribeProgress, resolveFileUrl } from "@/lib/api";
import type { SSEEvent } from "@/lib/types";

interface Props {
  actionId: string;
  onComplete?: () => void;
}

interface FrameData {
  index: number;
  url: string;
}

export default function FrameProgress({ actionId, onComplete }: Props) {
  const [frames, setFrames] = useState<FrameData[]>([]);
  const [totalFrames, setTotalFrames] = useState<number>(0);
  const [status, setStatus] = useState<string>("connecting");
  const [gifUrl, setGifUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = subscribeProgress(
      actionId,
      (data) => {
        const evt = data as unknown as SSEEvent;

        switch (evt.event) {
          case "frame_complete":
            if (evt.total_frames) setTotalFrames(evt.total_frames);
            if (evt.image_url != null && evt.frame_index != null) {
              const resolved = resolveFileUrl(evt.image_url) || evt.image_url;
              setFrames((prev) => [
                ...prev,
                { index: evt.frame_index!, url: resolved },
              ]);
            }
            setStatus("generating");
            break;
          case "postprocessing":
            setStatus("postprocessing");
            break;
          case "completed":
            setStatus("completed");
            if (evt.gif_url) setGifUrl(resolveFileUrl(evt.gif_url));
            es.close();
            onComplete?.();
            break;
          case "error":
            setStatus("error");
            setError(evt.message || "Unknown error");
            es.close();
            break;
          case "cancelled":
            setStatus("cancelled");
            es.close();
            break;
        }
      },
      () => {
        // SSE error - connection lost
        setStatus("disconnected");
      }
    );
    esRef.current = es;

    return () => es.close();
  }, [actionId, onComplete]);

  const handleCancel = async () => {
    try {
      await cancelAction(actionId);
    } catch {
      // ignore
    }
  };

  const progress = totalFrames > 0 ? (frames.length / totalFrames) * 100 : 0;

  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl p-4">
      {/* Status bar */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm">
          {status === "generating" && `Generating: ${frames.length}/${totalFrames} frames`}
          {status === "postprocessing" && "Post-processing..."}
          {status === "completed" && `Done! ${frames.length} frames`}
          {status === "error" && `Error: ${error}`}
          {status === "cancelled" && `Cancelled (${frames.length} frames)`}
          {status === "connecting" && "Connecting..."}
          {status === "disconnected" && "Connection lost"}
        </span>
        {status === "generating" && (
          <button
            onClick={handleCancel}
            className="px-3 py-1 text-xs bg-[var(--danger)] hover:bg-[var(--danger-hover)] rounded transition-colors"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Progress bar */}
      {totalFrames > 0 && status !== "completed" && (
        <div className="h-1.5 bg-[var(--border)] rounded-full mb-4 overflow-hidden">
          <div
            className="h-full bg-[var(--accent)] rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Completed GIF */}
      {gifUrl && status === "completed" && (
        <div className="mb-4 flex justify-center bg-black rounded-lg p-2">
          <img
            src={gifUrl}
            alt="Animation"
            className="h-32 object-contain"
            style={{ imageRendering: "pixelated" }}
          />
        </div>
      )}

      {/* Frame strip (live) */}
      {frames.length > 0 && (
        <div className="flex gap-1 overflow-x-auto pb-2">
          {frames
            .sort((a, b) => a.index - b.index)
            .map((f) => (
              <img
                key={f.index}
                src={f.url}
                alt={`Frame ${f.index}`}
                className="h-16 w-16 flex-shrink-0 object-contain bg-black rounded"
                style={{ imageRendering: "pixelated" }}
              />
            ))}
        </div>
      )}
    </div>
  );
}
