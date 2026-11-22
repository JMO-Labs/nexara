/**
 * @file lib/api/dailyQuestions.ts
 * @brief Daily-question bank: member suggestions and admin moderation.
 */
import { apiGet, apiPost, seg } from "./client";

/** @brief One question-bank row. */
export interface BankQuestion {
  id: string;
  text: string;
  source: "builtin" | "admin" | "member";
  status: "approved" | "pending" | "rejected";
  suggested_by: string | null;
  created_at: string;
}

/**
 * @brief Suggest a question (pending until an admin approves; 3/day).
 * @param text question text, max 280 chars
 * @return created row
 */
export const suggestQuestion = (text: string) =>
  apiPost<BankQuestion>("/api/v1/daily-questions/suggest", { text });

/**
 * @brief List bank questions by status (admin).
 * @param status approved | pending | rejected
 * @return rows
 */
export const listQuestions = (status: BankQuestion["status"] = "pending") =>
  apiGet<BankQuestion[]>(`/api/v1/admin/daily-questions?status=${status}`);

/**
 * @brief Add an approved question (admin).
 * @param text question text
 * @return created row
 */
export const addQuestion = (text: string) =>
  apiPost<BankQuestion>("/api/v1/admin/daily-questions", { text });

/**
 * @brief Approve or reject a pending question (admin).
 * @param id question id
 * @param action approve | reject
 * @return updated row
 */
export const moderateQuestion = (id: string, action: "approve" | "reject") =>
  apiPost<BankQuestion>(`/api/v1/admin/daily-questions/${seg(id)}/${action}`);
