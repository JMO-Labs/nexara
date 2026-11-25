/**
 * @file lib/api/adminSystem.ts
 * @brief Admin system health snapshot (GET /api/v1/admin/system).
 */
import { apiGet } from "./client";

export type ComponentStatus = "ok" | "warn" | "down";

export interface SystemComponent {
  name: string;
  status: ComponentStatus;
  detail: string;
}

export interface DiskInfo {
  external: boolean;
  total_bytes: number | null;
  used_bytes: number | null;
  used_pct: number | null;
  db_bytes: number | null;
  top_tables: { name: string; bytes: number }[];
}

export interface RuntimeInfo {
  version: string;
  alembic_head: string | null;
  uptime_seconds: number;
  cpu_percent: number;
  mem_total_bytes: number;
  mem_used_bytes: number;
  mem_limit_bytes: number | null;
}

export interface SystemHealth {
  components: SystemComponent[];
  disk: DiskInfo;
  runtime: RuntimeInfo;
  grafana_url?: string | null;
}

export const getSystemHealth = () =>
  apiGet<SystemHealth>("/api/v1/admin/system");
