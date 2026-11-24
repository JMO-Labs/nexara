/**
 * @file components/admin/system/RuntimePanel.tsx
 * @brief Version, uptime, CPU and memory facts.
 */
import { formatBytes } from "@/lib/formatBytes";
import type { RuntimeInfo } from "@/lib/api/adminSystem";

/**
 * @brief Human uptime, e.g. "2d 3h 4m".
 * @param s uptime in seconds
 * @return formatted text
 */
export function formatUptime(s: number): string {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  return [d && `${d}d`, (d || h) && `${h}h`, `${m}m`].filter(Boolean).join(" ");
}

/**
 * @brief Runtime facts card.
 * @param runtime runtime info
 * @return section element
 */
export function RuntimePanel({ runtime: r }: { runtime: RuntimeInfo }) {
  const mem = r.mem_limit_bytes ?? r.mem_total_bytes;
  const rows: [string, string][] = [
    ["Version", r.version],
    ["Migration", r.alembic_head ?? "Unknown"],
    ["Uptime", formatUptime(r.uptime_seconds)],
    ["CPU", `${Math.round(r.cpu_percent)}%`],
    ["Memory", `${formatBytes(r.mem_used_bytes)} of ${formatBytes(mem)}`],
  ];
  return (
    <section
      aria-labelledby="sys-runtime"
      className="glass-item rounded-[22px] p-4"
    >
      <h3 id="sys-runtime" className="text-sm font-semibold">
        Runtime
      </h3>
      <dl className="mt-2 space-y-1 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3">
            <dt className="text-muted">{k}</dt>
            <dd className="min-w-0 break-all text-right">{v}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
