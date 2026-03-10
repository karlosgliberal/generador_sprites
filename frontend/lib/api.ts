import type { Avatar, Action, Frame } from "./types";

const BASE = "/api";
const BACKEND = "http://localhost:8000";
const SSE_BASE = `${BACKEND}/api`;

/** Convert a relative /api/files/... URL to an absolute backend URL */
export function resolveFileUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("http")) return url;
  return `${BACKEND}${url}`;
}

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

// Avatars
export const listAvatars = () => fetchJSON<Avatar[]>("/avatars");

export const getAvatar = (id: string) => fetchJSON<Avatar>(`/avatars/${id}`);

export const createAvatar = (description: string, character_name?: string) =>
  fetchJSON<Avatar>("/avatars", {
    method: "POST",
    body: JSON.stringify({ description, character_name }),
  });

export const deleteAvatar = (id: string) =>
  fetchJSON<{ ok: boolean }>(`/avatars/${id}`, { method: "DELETE" });

// Actions
export const listActions = (avatarId: string) =>
  fetchJSON<Action[]>(`/avatars/${avatarId}/actions`);

export const createAction = (avatarId: string, action_name: string) =>
  fetchJSON<Action>(`/avatars/${avatarId}/actions`, {
    method: "POST",
    body: JSON.stringify({ action_name }),
  });

export const getAction = (actionId: string) =>
  fetchJSON<Action>(`/actions/${actionId}`);

export const getActionFrames = (actionId: string) =>
  fetchJSON<Frame[]>(`/actions/${actionId}/frames`);

export const cancelAction = (actionId: string) =>
  fetchJSON<{ ok: boolean }>(`/actions/${actionId}/cancel`, { method: "POST" });

export const deleteAction = (actionId: string) =>
  fetchJSON<{ ok: boolean }>(`/actions/${actionId}`, { method: "DELETE" });

// SSE
export function subscribeProgress(
  actionId: string,
  onMessage: (data: Record<string, unknown>) => void,
  onError?: (err: Event) => void
): EventSource {
  const es = new EventSource(`${SSE_BASE}/actions/${actionId}/progress`);
  es.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {
      // ignore parse errors
    }
  };
  if (onError) es.onerror = onError;
  return es;
}
