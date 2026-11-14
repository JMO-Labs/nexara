/**
 * @file lib/api/nudges.ts
 * @brief Nudge endpoint client.
 */
import { apiPost, seg } from "./client";

export interface Nudge {
  id: string;
  sender_id: string;
  target_id: string;
  nudge_type: string;
  created_at: string;
}

/**
 * @brief Nudge a user.
 * @param userId target user id
 * @param message optional message
 * @return created nudge
 */
export const sendNudge = (userId: string, message?: string) =>
  apiPost<Nudge>(`/api/v1/nudges/${seg(userId)}`, message ? { message } : {});
