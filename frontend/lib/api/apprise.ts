/**
 * @file lib/api/apprise.ts
 * @brief Apprise notification URL client. Responses never contain the URL.
 */
import { apiGet, apiPost, apiPatch, apiDelete, seg } from "./client";

export interface AppriseUrl {
  id: string;
  label: string;
  service: string | null;
  enabled: boolean;
}

export interface AppriseCreate {
  url: string;
  label: string;
  enabled: boolean;
}

export type AppriseUpdate = Partial<AppriseCreate>;

export interface AppriseTestResult {
  status: string;
  message: string;
}

const BASE = "/api/v1/apprise/urls";
const SCHEME = /^([a-z][a-z0-9+.-]*):\/\/\S+$/i;

/**
 * @brief Extract the Apprise service from a URL scheme.
 * @param url raw Apprise URL
 * @return lowercase scheme, or null when the URL is malformed
 */
export function serviceFromUrl(url: string): string | null {
  const m = SCHEME.exec(url.trim());
  return m ? m[1].toLowerCase() : null;
}

export const listAppriseUrls = () => apiGet<AppriseUrl[]>(BASE);
export const createAppriseUrl = (b: AppriseCreate) =>
  apiPost<AppriseUrl>(BASE, b);
export const updateAppriseUrl = (id: string, b: AppriseUpdate) =>
  apiPatch<AppriseUrl>(`${BASE}/${seg(id)}`, b);
export const deleteAppriseUrl = (id: string) => apiDelete(`${BASE}/${seg(id)}`);
export const testAppriseUrl = (id: string) =>
  apiPost<AppriseTestResult>(`${BASE}/${seg(id)}/test`);
