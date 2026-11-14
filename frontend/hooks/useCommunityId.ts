"use client";
/**
 * @file hooks/useCommunityId.ts
 * @brief Current viewer's community id from the session store.
 */
import { useSession } from "@/stores/session";

/** Fallback scope used before the session has loaded. */
export const DEFAULT_COMMUNITY = "default";

/**
 * @brief Community id of the signed-in user.
 * @return community id, or DEFAULT_COMMUNITY when unknown
 */
export function useCommunityId(): string {
  return useSession((s) => s.user?.community_id) ?? DEFAULT_COMMUNITY;
}
