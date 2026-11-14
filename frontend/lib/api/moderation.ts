/**
 * @file lib/api/moderation.ts
 * @brief Moderation endpoints: reports, admin queue, user blocking.
 */
import { apiDelete, apiGet, apiPost, seg } from "./client";

export type ReportTarget = "post" | "comment" | "message" | "media";
export type ReportReason =
  | "spam"
  | "harassment"
  | "inappropriate"
  | "misinformation"
  | "other";
export type ReportActionType =
  | "dismiss"
  | "warn_user"
  | "hide_content"
  | "delete_content"
  | "ban_user";

export interface ReportInput {
  target_type: ReportTarget;
  target_id: string;
  reason: ReportReason;
  description?: string;
}

export interface Report {
  id: string;
  reporter_id: string;
  target_type: ReportTarget;
  target_id: string;
  reason: ReportReason;
  description: string | null;
  status: "pending" | "reviewed" | "dismissed";
  action_taken?: string | null;
  admin_notes?: string | null;
  created_at: string;
}

export interface ReportPage {
  items: Report[];
  next_cursor: string | null;
  has_more: boolean;
}

/** @brief Submit a content report. @param body report payload */
export const createReport = (body: ReportInput) =>
  apiPost<{ id: string; status: string }>("/moderation/reports", body);

/** @brief Block a user. @param userId user to block */
export const blockUser = (userId: string) =>
  apiPost<{ id: string }>(`/users/${seg(userId)}/block`);

/** @brief Unblock a user. @param userId user to unblock */
export const unblockUser = (userId: string) =>
  apiDelete(`/users/${seg(userId)}/block`);

/** @brief List reports (admin). @param status filter */
export const listReports = (status: string = "pending") =>
  apiGet<ReportPage>(`/admin/moderation/reports?status=${seg(status)}`);

/** @brief Apply an admin action to a report. */
export const reportAction = (
  id: string,
  action: ReportActionType,
  note?: string,
) =>
  apiPost<{ id: string; status: string }>(
    `/admin/moderation/reports/${seg(id)}/action`,
    { action, note: note || undefined },
  );
