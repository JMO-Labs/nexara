/**
 * @file lib/api/adminApprise.ts
 * @brief Admin Apprise alert targets and member local-address opt-in.
 *        Responses never contain the target URL, only its scheme.
 */
import { apiGet, apiPost, apiPut, apiDelete, seg } from "./client";
import type { AppriseCreate, AppriseTestResult, AppriseUrl } from "./apprise";

export type AdminTarget = AppriseUrl;

const BASE = "/api/v1/admin/apprise";

export const listTargets = () => apiGet<AdminTarget[]>(`${BASE}/targets`);
export const createTarget = (b: AppriseCreate) =>
  apiPost<AdminTarget>(`${BASE}/targets`, b);
export const deleteTarget = (id: string) =>
  apiDelete(`${BASE}/targets/${seg(id)}`);
export const testTarget = (id: string) =>
  apiPost<AppriseTestResult>(`${BASE}/targets/${seg(id)}/test`);
export const getAppriseSettings = () =>
  apiGet<{ allow_local: boolean }>(`${BASE}/settings`);
export const putAppriseSettings = (allow_local: boolean) =>
  apiPut<{ allow_local: boolean }>(`${BASE}/settings`, { allow_local });
