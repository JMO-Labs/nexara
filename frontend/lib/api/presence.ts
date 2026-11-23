/**
 * @file lib/api/presence.ts
 * @brief Batch online-status lookup client.
 */
import { apiPost } from "./client";

export interface PresenceResult {
  online: string[];
  last_seen: Record<string, string | null>;
}

/** Server cap per request. */
export const PRESENCE_MAX_IDS = 200;

/**
 * @brief Ask which of the given users are online (privacy applied server-side).
 * @param userIds 1..200 user ids
 * @return online ids and last_seen map
 */
export const fetchPresence = (userIds: string[]) =>
  apiPost<PresenceResult>("/api/v1/presence", { user_ids: userIds });
