/**
 * @file lib/api/auditLog.ts
 * @brief Wrappers for the filtered admin audit log and its CSV export.
 */
import { apiGet } from "./client";
import type { AuditLogEntry, PaginatedResponse } from "./admin";

export interface AuditFilters {
  q: string;
  /** Action prefix such as "oauth." or empty. */
  action: string;
  /** yyyy-mm-dd (local start of day), or empty. */
  since: string;
  /** yyyy-mm-dd, inclusive (local end of day), or empty. */
  until: string;
}

const BASE = "/api/v1/admin/audit";

/** @brief Query string for the active filters (empty ones are dropped). */
export function auditQuery(
  f: AuditFilters,
  cursor?: string | null,
  limit?: number,
): string {
  const p = new URLSearchParams();
  if (f.q.trim()) p.set("q", f.q.trim());
  if (f.action) p.set("action_prefix", f.action);
  if (f.since) p.set("since", new Date(`${f.since}T00:00:00`).toISOString());
  if (f.until) {
    const end = new Date(`${f.until}T00:00:00`);
    end.setDate(end.getDate() + 1);
    p.set("until", end.toISOString());
  }
  if (cursor) p.set("cursor", cursor);
  if (limit) p.set("limit", String(limit));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const listAudit = (f: AuditFilters, cursor?: string | null) =>
  apiGet<PaginatedResponse<AuditLogEntry>>(
    `${BASE}${auditQuery(f, cursor, 50)}`,
  );

/** @brief Filtered CSV export as text (server caps at 50 000 rows). */
export const exportAuditCsv = (f: AuditFilters) =>
  apiGet<string>(`${BASE}.csv${auditQuery(f)}`);
