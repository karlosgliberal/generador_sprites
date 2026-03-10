"use client";

import { useState } from "react";

const AVAILABLE_ACTIONS = [
  "idle",
  "walk",
  "run",
  "jump",
  "punch",
  "death",
  "sword_attack",
];

interface Props {
  existingActions: string[];
  onGenerate: (actionName: string) => void;
  disabled?: boolean;
}

export default function GenerationControls({
  existingActions,
  onGenerate,
  disabled,
}: Props) {
  const [selected, setSelected] = useState("");
  const available = AVAILABLE_ACTIONS.filter(
    (a) => !existingActions.includes(a)
  );

  return (
    <div className="flex gap-2 items-center">
      <select
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        disabled={disabled || available.length === 0}
        className="bg-[var(--card)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm disabled:opacity-50"
      >
        <option value="">Add action...</option>
        {available.map((a) => (
          <option key={a} value={a}>
            {a}
          </option>
        ))}
      </select>
      <button
        onClick={() => {
          if (selected) {
            onGenerate(selected);
            setSelected("");
          }
        }}
        disabled={!selected || disabled}
        className="px-4 py-2 bg-[var(--accent)] hover:bg-[var(--accent-hover)] disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
      >
        Generate
      </button>
    </div>
  );
}
