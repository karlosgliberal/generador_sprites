"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createAvatar } from "@/lib/api";

const PRESETS = [
  { name: "ninja", label: "Ninja" },
  { name: "knight", label: "Knight" },
  { name: "cat", label: "Shadow Cat" },
  { name: "monk", label: "Monk" },
  { name: "rabbit", label: "Wizard Rabbit" },
];

export default function CreatePage() {
  const router = useRouter();
  const [mode, setMode] = useState<"preset" | "custom">("preset");
  const [selectedPreset, setSelectedPreset] = useState("");
  const [customDescription, setCustomDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    setLoading(true);
    setError(null);
    try {
      let avatar;
      if (mode === "preset" && selectedPreset) {
        avatar = await createAvatar("", selectedPreset);
      } else if (mode === "custom" && customDescription.trim()) {
        avatar = await createAvatar(customDescription.trim());
      } else {
        setError("Please select a preset or enter a description");
        setLoading(false);
        return;
      }
      router.push(`/avatars/${avatar.id}`);
    } catch (e) {
      setError(`${e}`);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Create Avatar</h2>

      {/* Mode toggle */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setMode("preset")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === "preset"
              ? "bg-[var(--accent)] text-white"
              : "bg-[var(--card)] border border-[var(--border)]"
          }`}
        >
          Preset Character
        </button>
        <button
          onClick={() => setMode("custom")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === "custom"
              ? "bg-[var(--accent)] text-white"
              : "bg-[var(--card)] border border-[var(--border)]"
          }`}
        >
          Custom Description
        </button>
      </div>

      {mode === "preset" ? (
        <div className="grid grid-cols-2 gap-3 mb-6">
          {PRESETS.map((p) => (
            <button
              key={p.name}
              onClick={() => setSelectedPreset(p.name)}
              className={`p-4 rounded-xl border text-left transition-colors ${
                selectedPreset === p.name
                  ? "border-[var(--accent)] bg-[var(--accent)]/10"
                  : "border-[var(--border)] bg-[var(--card)] hover:border-[var(--accent)]/50"
              }`}
            >
              <span className="font-medium">{p.label}</span>
            </button>
          ))}
        </div>
      ) : (
        <textarea
          value={customDescription}
          onChange={(e) => setCustomDescription(e.target.value)}
          placeholder="Describe your character... e.g., 'wizard cat with a blue hat and magic staff'"
          className="w-full h-32 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 text-sm resize-none focus:border-[var(--accent)] focus:outline-none mb-6"
        />
      )}

      {error && (
        <div className="text-[var(--danger)] text-sm mb-4">{error}</div>
      )}

      <button
        onClick={handleCreate}
        disabled={loading}
        className="w-full py-3 bg-[var(--accent)] hover:bg-[var(--accent-hover)] disabled:opacity-50 rounded-xl font-medium transition-colors"
      >
        {loading ? "Generating avatar..." : "Create Avatar"}
      </button>

      {loading && (
        <p className="text-[var(--muted)] text-sm mt-3 text-center">
          This takes ~5 seconds (one Gemini call)
        </p>
      )}
    </div>
  );
}
