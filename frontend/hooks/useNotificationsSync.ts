"use client";
/**
 * @file hooks/useNotificationsSync.ts
 * @brief Multi-tab sync: invalidate react-query caches on SSE events.
 */
import { useQueryClient } from "@tanstack/react-query";
import { STREAM_PATH } from "@/lib/api/notifications";
import { useSSE } from "@/hooks/useSSE";
import { useSession } from "@/stores/session";
import { PREFS_KEY } from "@/components/settings/SnoozeControls";

export const SYNC_EVENT_TYPES = [
  "user_notification_dismissed",
  "user_preferences_updated",
] as const;

/**
 * @brief Returns an SSE handler invalidating caches per event type.
 * @return handler (data, type)
 */
export function useSyncHandler() {
  const qc = useQueryClient();
  return (_data: unknown, type: string) => {
    if (type === "user_notification_dismissed") {
      void qc.invalidateQueries({ queryKey: ["notifications"] });
    } else if (type === "user_preferences_updated") {
      void qc.invalidateQueries({ queryKey: PREFS_KEY });
    }
  };
}

/**
 * @brief Subscribe to sync events while authenticated.
 * @param types event types to react to (default: all sync events)
 */
export function useNotificationsSync(
  types: readonly string[] = SYNC_EVENT_TYPES,
): void {
  const isAuthed = useSession((s) => s.status === "authenticated");
  const onMessage = useSyncHandler();
  useSSE(STREAM_PATH, { enabled: isAuthed, eventTypes: types, onMessage });
}
