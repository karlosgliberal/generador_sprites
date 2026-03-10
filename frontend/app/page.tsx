"use client";

import { useEffect, useState } from "react";
import { listAvatars, deleteAvatar } from "@/lib/api";
import type { Avatar } from "@/lib/types";
import AvatarCard from "@/components/AvatarCard";

export default function Home() {
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const data = await listAvatars();
      setAvatars(data);
    } catch {
      // API not ready
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleDelete = async (id: string) => {
    try {
      await deleteAvatar(id);
      setAvatars((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      alert(`Error: ${e}`);
    }
  };

  if (loading) {
    return <div className="text-[var(--muted)]">Loading...</div>;
  }

  if (avatars.length === 0) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold mb-2">No avatars yet</h2>
        <p className="text-[var(--muted)] mb-6">
          Create your first pixel art character
        </p>
        <a
          href="/create"
          className="inline-block px-6 py-3 bg-[var(--accent)] hover:bg-[var(--accent-hover)] rounded-lg font-medium transition-colors"
        >
          Create Avatar
        </a>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Your Avatars</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {avatars.map((avatar) => (
          <AvatarCard key={avatar.id} avatar={avatar} onDelete={handleDelete} />
        ))}
      </div>
    </div>
  );
}
