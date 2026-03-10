"use client";

import type { Action } from "@/lib/types";
import { resolveFileUrl } from "@/lib/api";

interface Props {
  action: Action;
  onDelete: (id: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  generating: "text-yellow-400",
  completed: "text-[var(--success)]",
  failed: "text-[var(--danger)]",
  cancelled: "text-[var(--muted)]",
  pending: "text-[var(--muted)]",
};

export default function ActionCard({ action, onDelete }: Props) {
  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl overflow-hidden">
      <div className="aspect-[3/1] bg-black flex items-center justify-center">
        {action.gif_url && action.status === "completed" ? (
          <img
            src={resolveFileUrl(action.gif_url) || ""}
            alt={action.action_name}
            className="h-full object-contain"
            style={{ imageRendering: "pixelated" }}
          />
        ) : action.status === "generating" ? (
          <div className="text-yellow-400 text-sm animate-pulse">
            Generating...
          </div>
        ) : (
          <div className="text-[var(--muted)] text-sm">{action.status}</div>
        )}
      </div>
      <div className="p-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium capitalize">{action.action_name}</h4>
          <span className={`text-xs ${STATUS_COLORS[action.status] || ""}`}>
            {action.status}
            {action.frame_count ? ` (${action.frame_count} frames)` : ""}
          </span>
        </div>
        <div className="mt-2 flex gap-2">
          {action.strip_url && (
            <a
              href={action.strip_url}
              target="_blank"
              className="text-xs text-[var(--accent)] hover:underline"
            >
              Strip
            </a>
          )}
          <button
            onClick={() => {
              const msg =
                action.status === "generating"
                  ? "Cancel and delete this action?"
                  : `Delete ${action.action_name}?`;
              if (confirm(msg)) onDelete(action.id);
            }}
            className="text-xs text-[var(--danger)] hover:text-[var(--danger-hover)] ml-auto"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
