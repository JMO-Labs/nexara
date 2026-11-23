"use client";
/**
 * @file components/layout/PresenceSync.tsx
 * @brief Renders nothing. Refreshes watched presence every 60 s and on
 *        every SSE (re)connect. Mount once, only when signed in.
 */
import { useEffect } from "react";
import { useSSE } from "@/hooks/useSSE";
import { STREAM_PATH } from "@/lib/api/notifications";
import { flushPresence } from "@/stores/presence";

export const PRESENCE_TICK_MS = 60_000;

/** @return null */
export function PresenceSync() {
  useEffect(() => {
    const t = setInterval(() => void flushPresence(), PRESENCE_TICK_MS);
    return () => clearInterval(t);
  }, []);
  useSSE(STREAM_PATH, {
    eventTypes: ["connected"],
    onMessage: () => void flushPresence(),
  });
  return null;
}
