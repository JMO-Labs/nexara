"use client";
/**
 * @file stores/presence.ts
 * @brief Ref-counted presence watches batched into one request per tick.
 *        Avatars call `useOnline(id)`; `PresenceSync` drives `flush()`.
 */
import { useEffect } from "react";
import { create } from "zustand";
import { fetchPresence, PRESENCE_MAX_IDS } from "@/lib/api/presence";

/** Debounce for newly watched ids. */
export const NEW_ID_DEBOUNCE_MS = 300;

interface PresenceState {
  online: Record<string, true>;
}

export const usePresenceStore = create<PresenceState>(() => ({ online: {} }));

const counts = new Map<string, number>();
let timer: ReturnType<typeof setTimeout> | null = null;

/**
 * @brief Post all watched ids (chunked at 200) and store who is online.
 */
export async function flushPresence(): Promise<void> {
  const ids = [...counts.keys()];
  for (let i = 0; i < ids.length; i += PRESENCE_MAX_IDS) {
    const chunk = ids.slice(i, i + PRESENCE_MAX_IDS);
    try {
      const res = await fetchPresence(chunk);
      const on = new Set(res.online);
      usePresenceStore.setState((s) => {
        const next = { ...s.online };
        for (const id of chunk) {
          if (on.has(id)) next[id] = true;
          else delete next[id];
        }
        return { online: next };
      });
    } catch {
      // Best effort; the next tick retries.
    }
  }
}

/**
 * @brief Start watching ids (ref-counted); new ids trigger a debounced flush.
 * @param ids user ids
 */
export function watchPresence(ids: string[]): void {
  let added = false;
  for (const id of ids) {
    const n = counts.get(id) ?? 0;
    if (n === 0) added = true;
    counts.set(id, n + 1);
  }
  if (!added) return;
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    timer = null;
    void flushPresence();
  }, NEW_ID_DEBOUNCE_MS);
}

/**
 * @brief Release watches; ids reaching zero are dropped.
 * @param ids user ids
 */
export function unwatchPresence(ids: string[]): void {
  const gone: string[] = [];
  for (const id of ids) {
    const n = (counts.get(id) ?? 0) - 1;
    if (n > 0) counts.set(id, n);
    else if (counts.delete(id)) gone.push(id);
  }
  if (!gone.length) return;
  usePresenceStore.setState((s) => {
    const next = { ...s.online };
    for (const id of gone) delete next[id];
    return { online: next };
  });
}

/** @brief Test helper: drop all watches, timers and results. */
export function resetPresence(): void {
  counts.clear();
  if (timer) clearTimeout(timer);
  timer = null;
  usePresenceStore.setState({ online: {} });
}

/**
 * @brief Watch one user while mounted.
 * @param userId user id (undefined = no watch)
 * @return true when the user is online and visible to the viewer
 */
export function useOnline(userId?: string): boolean {
  useEffect(() => {
    if (!userId) return;
    watchPresence([userId]);
    return () => unwatchPresence([userId]);
  }, [userId]);
  return usePresenceStore((s) => (userId ? !!s.online[userId] : false));
}
