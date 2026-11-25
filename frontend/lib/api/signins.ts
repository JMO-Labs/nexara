/**
 * @file lib/api/signins.ts
 * @brief Wrappers for the admin sign-in log and the member device list.
 */
import { apiDelete, apiGet, apiPost, seg } from "./client";
import type { MessageResponse } from "./auth";

export interface SigninRow {
  id: string;
  time: string;
  email: string | null;
  user: string | null;
  method: string;
  success: boolean;
  reason: string | null;
  ip: string | null;
  device: string | null;
}

export interface SigninPage {
  items: SigninRow[];
  next_cursor: string | null;
}

export interface SigninFilters {
  q: string;
  success: "" | "true" | "false";
  method: string;
  /** yyyy-mm-dd (local start of day), or empty. */
  since: string;
}

export interface DeviceSession {
  family_id: string;
  device: string;
  ip: string | null;
  last_seen: string;
  current: boolean;
}

const BASE = "/api/v1/admin/signins";
/** Under /auth so the path-scoped refresh cookie is sent (current-device detection). */
const SESS = "/api/v1/auth/sessions";

/** @brief Query string for the active filters (empty ones are dropped). */
export function signinQuery(f: SigninFilters, cursor?: string | null): string {
  const p = new URLSearchParams();
  if (f.q.trim()) p.set("q", f.q.trim());
  if (f.success) p.set("success", f.success);
  if (f.method) p.set("method", f.method);
  if (f.since) p.set("since", new Date(`${f.since}T00:00:00`).toISOString());
  if (cursor) p.set("cursor", cursor);
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const listSignins = (f: SigninFilters, cursor?: string | null) =>
  apiGet<SigninPage>(`${BASE}${signinQuery(f, cursor)}`);

/** @brief Filtered CSV export as text (server caps at 50 000 rows). */
export const exportSigninsCsv = (f: SigninFilters) =>
  apiGet<string>(`${BASE}.csv${signinQuery(f)}`);

export const listSessions = () => apiGet<DeviceSession[]>(SESS);

export const revokeSession = (familyId: string) =>
  apiDelete<MessageResponse>(`${SESS}/${seg(familyId)}`);

export const revokeOtherSessions = () =>
  apiPost<MessageResponse>(`${SESS}/revoke-others`);
