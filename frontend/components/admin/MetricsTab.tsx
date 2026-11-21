"use client";
/**
 * @file components/admin/MetricsTab.tsx
 * @brief Admin metrics display with community, system and WAF stats.
 */
import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useAdminMetrics } from "@/hooks/useAdmin";
import { Panel } from "@/components/ui/page";
import { listItem, listStagger } from "@/components/ui/motion";
import { AdminLoading, AdminNotice } from "./AdminState";

function formatBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIdx = 0;
  while (size >= 1024 && unitIdx < units.length - 1) {
    size /= 1024;
    unitIdx += 1;
  }
  return `${size.toFixed(1)} ${units[unitIdx]}`;
}

/**
 * @brief Human uptime: "<1 min", "N min" under an hour, else "Nd Nh".
 * @param seconds uptime in seconds
 * @return formatted uptime
 */
function formatSeconds(seconds: number): string {
  if (seconds < 60) return "<1 min";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return `${days}d ${hours}h`;
}

/** @brief KPI tile: big tabular number over a label. */
function KpiTile({ label, value }: { label: string; value: string | number }) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      data-testid="metric-card"
      className="glass-item flex flex-col gap-1 rounded-[22px] p-4 text-ink"
      {...(reduced ? {} : { variants: listItem })}
    >
      <span className="text-sm text-muted">{label}</span>
      <span className="text-[28px] font-medium tracking-tight tabular-nums">
        {value}
      </span>
    </motion.div>
  );
}

/** @brief Stat row: label left, tabular value right. */
function StatRow({ label, value }: { label: string; value: string | number }) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      data-testid="metric-card"
      className="flex items-center justify-between gap-3 py-2.5"
      {...(reduced ? {} : { variants: listItem })}
    >
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="text-sm font-semibold tabular-nums text-ink">{value}</dd>
    </motion.div>
  );
}

/** @brief Container that staggers its children in on mount. */
function Stagger({
  as = "div",
  className,
  children,
}: {
  as?: "div" | "dl";
  className?: string;
  children: React.ReactNode;
}) {
  const reduced = useReducedMotion();
  const Tag = motion[as];
  return (
    <Tag
      className={className}
      {...(reduced
        ? {}
        : { variants: listStagger, initial: "hidden", animate: "show" })}
    >
      {children}
    </Tag>
  );
}

/**
 * @brief Admin metrics: KPI tiles plus stat-row panels.
 * @return metrics content
 */
export function MetricsTab() {
  const { data: metrics, isLoading, error } = useAdminMetrics();

  if (isLoading) return <AdminLoading />;

  if (error) {
    return <AdminNotice tone="error">Failed to load metrics</AdminNotice>;
  }

  if (!metrics) return null;

  return (
    <div className="flex flex-col gap-4">
      <Panel title="Overview">
        <Stagger className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <KpiTile label="Total users" value={metrics.community.users_total} />
          <KpiTile
            label="Active (30d)"
            value={metrics.community.users_active_30d}
          />
          <KpiTile label="Posts (7d)" value={metrics.community.posts_last_7d} />
          <KpiTile
            label="Storage"
            value={formatBytes(metrics.community.media_storage_bytes)}
          />
        </Stagger>
      </Panel>

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Community">
          <Stagger as="dl">
            <StatRow
              label="Online now"
              value={metrics.community.users_online_now}
            />
            <StatRow
              label="Total posts"
              value={metrics.community.posts_total}
            />
            <StatRow
              label="Media files"
              value={metrics.community.media_files}
            />
          </Stagger>
        </Panel>

        <Panel title="System">
          <Stagger as="dl">
            <StatRow label="Version" value={metrics.system.version} />
            <StatRow
              label="Blocked requests today"
              value={metrics.waf.blocks_today}
            />
            {Object.entries(metrics.waf.blocks_by_reason).map(
              ([reason, count]) => (
                <StatRow
                  key={reason}
                  label={`${reason} blocks`}
                  value={count}
                />
              ),
            )}
            <StatRow
              label="Uptime"
              value={formatSeconds(metrics.system.uptime_seconds)}
            />
            {metrics.system.db_size_bytes && (
              <StatRow
                label="DB size"
                value={formatBytes(metrics.system.db_size_bytes)}
              />
            )}
            {metrics.system.valkey_memory_bytes && (
              <StatRow
                label="Valkey memory"
                value={formatBytes(metrics.system.valkey_memory_bytes)}
              />
            )}
            {metrics.system.celery_queue_depth !== undefined && (
              <StatRow
                label="Celery queue"
                value={metrics.system.celery_queue_depth ?? 0}
              />
            )}
          </Stagger>
        </Panel>
      </div>
    </div>
  );
}
