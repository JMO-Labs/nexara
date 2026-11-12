/**
 * @file lib/api/dataExport.ts
 * @brief Data export (GDPR-style "download my data") endpoints.
 */
import { apiGet, apiPost, seg } from "./client";

export type ExportState =
  "pending" | "processing" | "ready" | "expired" | "failed";

export interface DataExport {
  id: string;
  status: ExportState;
  created_at: string;
  expires_at: string | null;
  downloaded_at: string | null;
}

/** @brief Request a new export. @return the new export id */
export const requestExport = () =>
  apiPost<{ export_id: string }>("/export/request");

/** @brief Fetch status of one export. @param id export id */
export const getExportStatus = (id: string) =>
  apiGet<DataExport>(`/export/${seg(id)}/status`);

/** @brief List recent exports. @param limit max rows */
export const listExports = (limit = 5) =>
  apiGet<DataExport[]>(`/export?limit=${limit}`);
