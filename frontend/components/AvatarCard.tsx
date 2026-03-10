"use client";

import type { Avatar } from "@/lib/types";
import { resolveFileUrl } from "@/lib/api";

interface Props {
  avatar: Avatar;
  onDelete: (id: string) => void;
}

export default function AvatarCard({ avatar, onDelete }: Props) {
  return (
    <a
      href={`/avatars/${avatar.id}`}
      className="block bg-[var(--card)] border border-[var(--border)] rounded-xl overflow-hidden hover:border-[var(--accent)] transition-colors group"
    >
      <div className="aspect-square bg-black flex items-center justify-center">
        {avatar.avatar_image_url ? (
          <img
            src={resolveFileUrl(avatar.avatar_image_url) || ""}
            alt={avatar.description}
            className="w-full h-full object-contain image-rendering-pixelated"
            style={{ imageRendering: "pixelated" }}
          />
        ) : (
          <div className="text-[var(--muted)] text-sm">No image</div>
        )}
      </div>
      <div className="p-4">
        <h3 className="font-medium truncate">
          {avatar.character_name || "Custom"}
        </h3>
        <p className="text-sm text-[var(--muted)] mt-1 line-clamp-2">
          {avatar.description}
        </p>
        <div className="mt-3 flex items-center justify-between">
          <span className="text-xs text-[var(--muted)]">
            {avatar.action_count} action{avatar.action_count !== 1 ? "s" : ""}
          </span>
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (confirm("Delete this avatar and all its actions?")) {
                onDelete(avatar.id);
              }
            }}
            className="text-xs text-[var(--danger)] hover:text-[var(--danger-hover)] opacity-0 group-hover:opacity-100 transition-opacity"
          >
            Delete
          </button>
        </div>
      </div>
    </a>
  );
}
