"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getAvatar,
  listActions,
  createAction,
  deleteAction,
  deleteAvatar,
  resolveFileUrl,
} from "@/lib/api";
import type { Avatar, Action } from "@/lib/types";
import ActionCard from "@/components/ActionCard";
import FrameProgress from "@/components/FrameProgress";
import GenerationControls from "@/components/GenerationControls";

export default function AvatarDetailPage() {
  const params = useParams();
  const router = useRouter();
  const avatarId = params.id as string;

  const [avatar, setAvatar] = useState<Avatar | null>(null);
  const [actions, setActions] = useState<Action[]>([]);
  const [activeGeneration, setActiveGeneration] = useState<Action | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    try {
      const [av, acts] = await Promise.all([
        getAvatar(avatarId),
        listActions(avatarId),
      ]);
      setAvatar(av);
      setActions(acts);
      const generating = acts.find((a) => a.status === "generating");
      if (generating) setActiveGeneration(generating);
    } catch {
      // not found
    } finally {
      setLoading(false);
    }
  }, [avatarId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGenerate = async (actionName: string) => {
    try {
      const action = await createAction(avatarId, actionName);
      setActiveGeneration(action);
      setActions((prev) => [...prev, action]);
    } catch (e) {
      alert(`Error: ${e}`);
    }
  };

  const handleDeleteAction = async (actionId: string) => {
    try {
      await deleteAction(actionId);
      setActions((prev) => prev.filter((a) => a.id !== actionId));
      if (activeGeneration?.id === actionId) setActiveGeneration(null);
    } catch (e) {
      alert(`Error: ${e}`);
    }
  };

  const handleDeleteAvatar = async () => {
    if (!confirm("Delete this avatar and ALL its actions?")) return;
    try {
      await deleteAvatar(avatarId);
      router.push("/");
    } catch (e) {
      alert(`Error: ${e}`);
    }
  };

  const handleGenerationComplete = () => {
    setActiveGeneration(null);
    loadData();
  };

  if (loading) return <div className="text-[var(--muted)]">Loading...</div>;
  if (!avatar) return <div className="text-[var(--danger)]">Avatar not found</div>;

  const completedActions = actions.filter((a) => a.status === "completed");
  const existingActionNames = actions
    .filter((a) => a.status !== "failed" && a.status !== "cancelled")
    .map((a) => a.action_name);

  return (
    <div>
      {/* Avatar header */}
      <div className="flex gap-6 mb-8">
        <div className="w-48 h-48 bg-black rounded-xl overflow-hidden flex-shrink-0">
          {avatar.avatar_image_url && (
            <img
              src={resolveFileUrl(avatar.avatar_image_url) || ""}
              alt={avatar.description}
              className="w-full h-full object-contain"
              style={{ imageRendering: "pixelated" }}
            />
          )}
        </div>
        <div className="flex-1">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold">
                {avatar.character_name || "Custom Avatar"}
              </h2>
              <p className="text-[var(--muted)] mt-1">{avatar.description}</p>
            </div>
            <button
              onClick={handleDeleteAvatar}
              className="px-3 py-1 text-sm text-[var(--danger)] border border-[var(--danger)]/30 hover:bg-[var(--danger)]/10 rounded-lg transition-colors"
            >
              Delete Avatar
            </button>
          </div>
          <div className="mt-4">
            <GenerationControls
              existingActions={existingActionNames}
              onGenerate={handleGenerate}
              disabled={!!activeGeneration}
            />
          </div>
        </div>
      </div>

      {/* Active generation */}
      {activeGeneration && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-3 capitalize">
            Generating: {activeGeneration.action_name}
          </h3>
          <FrameProgress
            actionId={activeGeneration.id}
            onComplete={handleGenerationComplete}
          />
        </div>
      )}

      {/* Completed actions */}
      {completedActions.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-3">Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {completedActions.map((action) => (
              <ActionCard
                key={action.id}
                action={action}
                onDelete={handleDeleteAction}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
