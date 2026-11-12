"use client";
/**
 * @file components/admin/MetricsTab.tsx
 * @brief Admin metrics display with community, system, and WAF stats.
 */
import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useAdminMetrics } from "@/hooks/useAdmin";
import { Card } from "@/components/ui";
import { listItem, listStagger } from "@/components/ui/motion";
import { AdminLoading, AdminNotice } from "./AdminState";

const MotionCard = motion.create(Card);

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

function formatSeconds(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return `${days}d ${hours}h`;
}

/**
 * @brief Displays a metric card with label and value.
 */
function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  const reduced = useReducedMotion();
  return (
    <MotionCard
      data-testid="metric-card"
      className="flex flex-col gap-1 p-4"
      {...(reduced ? {} : { variants: listItem })}
    >
      <span className="text-sm text-muted">{label}</span>
      <span className="text-2xl font-black">{value}</span>
    </MotionCard>
  );
}

/** @brief Grid that staggers its MetricCards in on mount. */
function MetricGrid({
  className,
  children,
}: {
  className: string;
  children: React.ReactNode;
}) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className={className}
      {...(reduced
        ? {}
        : { variants: listStagger, initial: "hidden", animate: "show" })}
    >
      {children}
    </motion.div>
  );
}

const GRID = "grid grid-cols-2 gap-3";

export function MetricsTab() {
  const { data: metrics, isLoading, error } = useAdminMetrics();

  if (isLoading) return <AdminLoading />;

  if (error) {
    return <AdminNotice tone="error">Failed to load metrics</AdminNotice>;
  }

  if (!metrics) return null;

  return (
    <div className="flex flex-col gap-6">
      <section>
        <h3 className="mb-3 text-lg font-semibold">
          Key performance indicators
        </h3>
        <MetricGrid className={`${GRID} md:grid-cols-4`}>
          <MetricCard
            label="Total users"
            value={metrics.community.users_total}
          />
          <MetricCard
            label="Active (30d)"
            value={metrics.community.users_active_30d}
          />
          <MetricCard
            label="Posts (7d)"
            value={metrics.community.posts_last_7d}
          />
          <MetricCard
            label="Storage"
            value={formatBytes(metrics.community.media_storage_bytes)}
          />
        </MetricGrid>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <section>
          <h4 className="mb-3 font-semibold">Community</h4>
          <MetricGrid className={GRID}>
            <MetricCard
              label="Online now"
              value={metrics.community.users_online_now}
            />
            <MetricCard
              label="Total posts"
              value={metrics.community.posts_total}
            />
            <MetricCard
              label="Media files"
              value={metrics.community.media_files}
            />
          </MetricGrid>
        </section>

        <section>
          <h4 className="mb-3 font-semibold">System</h4>
          <MetricGrid className={GRID}>
            <MetricCard label="Version" value={metrics.system.version} />
            <MetricCard
              label="Uptime"
              value={formatSeconds(metrics.system.uptime_seconds)}
            />
            {metrics.system.db_size_bytes && (
              <MetricCard
                label="DB size"
                value={formatBytes(metrics.system.db_size_bytes)}
              />
            )}
            {metrics.system.valkey_memory_bytes && (
              <MetricCard
                label="Valkey memory"
                value={formatBytes(metrics.system.valkey_memory_bytes)}
              />
            )}
            {metrics.system.celery_queue_depth !== undefined && (
              <MetricCard
                label="Celery queue"
                value={metrics.system.celery_queue_depth ?? 0}
              />
            )}
          </MetricGrid>
        </section>
      </div>

      <section>
        <h4 className="mb-3 font-semibold">Security (WAF)</h4>
        <MetricGrid className={`${GRID} md:grid-cols-4`}>
          <MetricCard label="Blocks today" value={metrics.waf.blocks_today} />
          {Object.entries(metrics.waf.blocks_by_reason).map(
            ([reason, count]) => (
              <MetricCard
                key={reason}
                label={`${reason} blocks`}
                value={count}
              />
            ),
          )}
        </MetricGrid>
      </section>
    </div>
  );
}
