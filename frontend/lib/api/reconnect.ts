/**
 * @file lib/api/reconnect.ts
 * @brief Reconnect-reminder REST client (snooze a person for 90 days).
 */
import { apiPost } from "./client";

/**
 * @brief Stop reminding me about one person for 90 days.
 * @param targetId the relative's user id
 * @return when the snooze ends
 */
export const snoozeReconnect = (targetId: string) =>
  apiPost<{ until: string }>("/api/v1/reconnect/snooze", {
    target_id: targetId,
  });
