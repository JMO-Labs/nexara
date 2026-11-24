/**
 * @file lib/api/apprise.ts
 * @brief Apprise notification URL client. Responses never contain the URL.
 */
import { apiGet, apiPost, apiPatch, apiDelete, seg } from "./client";

export interface AppriseUrl {
  id: string;
  label: string | null;
  enabled: boolean;
  scheme: string;
  failure_count: number;
  last_failure_at: string | null;
  created_at: string;
}

export interface AppriseCreate {
  apprise_url: string;
  label?: string;
}

export interface AppriseUpdate {
  label?: string;
  enabled?: boolean;
}

export interface AppriseTestResult {
  status: string;
  message: string;
}

const BASE = "/api/v1/notifications/apprise";

export const listAppriseUrls = () => apiGet<AppriseUrl[]>(BASE);
export const createAppriseUrl = (b: AppriseCreate) =>
  apiPost<AppriseUrl>(BASE, b);
export const updateAppriseUrl = (id: string, b: AppriseUpdate) =>
  apiPatch<AppriseUrl>(`${BASE}/${seg(id)}`, b);
export const deleteAppriseUrl = (id: string) => apiDelete(`${BASE}/${seg(id)}`);
export const testAppriseUrl = (id: string) =>
  apiPost<AppriseTestResult>(`${BASE}/${seg(id)}/test`);
