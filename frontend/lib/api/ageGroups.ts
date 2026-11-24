/**
 * @file lib/api/ageGroups.ts
 * @brief Age group API: member suggestions and admin management.
 */
import { apiGet, apiPost, apiPut, seg } from "./client";

export type AgeGroup = "child" | "teen" | "adult";

/** @brief Display labels, including "unknown". */
export const AGE_LABEL: Record<AgeGroup | "unknown", string> = {
  child: "Child (under 13)",
  teen: "Teen (13–17)",
  adult: "Adult (18+)",
  unknown: "Not set",
};

export const AGE_GROUPS: AgeGroup[] = ["child", "teen", "adult"];

/** @brief Stored suggestion. */
export interface AgeSuggestion {
  id: string;
  subject_id: string;
  suggested_by: string;
  age_group: string;
  subject_name?: string | null;
  suggested_by_name?: string | null;
  note: string | null;
  status: string;
  created_at: string;
}

const ADMIN = "/api/v1/admin/age-groups";

export const suggestAgeGroup = (b: {
  subject_id: string;
  age_group: AgeGroup;
  note?: string;
}) => apiPost<AgeSuggestion>("/api/v1/age-groups/suggestions", b);
export const listSuggestions = () =>
  apiGet<AgeSuggestion[]>(`${ADMIN}/suggestions?status=pending`);
export const decideSuggestion = (id: string, approve: boolean) =>
  apiPost<AgeSuggestion>(
    `${ADMIN}/suggestions/${seg(id)}/${approve ? "approve" : "reject"}`,
  );
export const getAgeSettings = () =>
  apiGet<{ adult_requires_approval: boolean }>(`${ADMIN}/settings`);
export const putAgeSettings = (adult_requires_approval: boolean) =>
  apiPut<{ adult_requires_approval: boolean }>(`${ADMIN}/settings`, {
    adult_requires_approval,
  });
export const setUserAgeGroup = (id: string, age_group: AgeGroup | null) =>
  apiPut<{ message: string }>(`/api/v1/admin/users/${seg(id)}/age-group`, {
    age_group,
  });
