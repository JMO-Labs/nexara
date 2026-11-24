/**
 * @file components/admin/system/DiskPanel.tsx
 * @brief Disk usage bar (local storage) plus database size and top tables.
 */
import { formatBytes } from "@/lib/formatBytes";
import type { DiskInfo } from "@/lib/api/adminSystem";

/** Usage at or above this percent is drawn in the danger colour. */
export const DISK_WARN_PCT = 85;

/**
 * @brief Storage usage card.
 * @param disk disk info
 * @return section element
 */
export function DiskPanel({ disk }: { disk: DiskInfo }) {
  const pct = disk.used_pct == null ? null : Math.round(disk.used_pct);
  const valueText =
    pct == null
      ? undefined
      : disk.used_bytes != null && disk.total_bytes != null
        ? `${pct}% used, ${formatBytes(disk.used_bytes)} of ${formatBytes(disk.total_bytes)}`
        : `${pct}% used`;
  return (
    <section
      aria-labelledby="sys-disk"
      className="glass-item rounded-[22px] p-4"
    >
      <h3 id="sys-disk" className="text-sm font-semibold">
        Disk
      </h3>
      {disk.external || pct == null ? (
        <p className="mt-2 text-sm text-muted">
          Media is kept in external storage, so disk usage is not tracked here.
        </p>
      ) : (
        <div className="mt-2">
          <div
            role="progressbar"
            aria-label="Disk used"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuetext={valueText}
            className="h-2.5 w-full overflow-hidden rounded-full bg-border"
          >
            <div
              className={`h-full ${pct >= DISK_WARN_PCT ? "bg-danger" : "bg-accent"}`}
              style={{ width: `${Math.min(pct, 100)}%` }}
            />
          </div>
          <p className="mt-1 text-sm">
            {pct}% used
            {disk.used_bytes != null && disk.total_bytes != null && (
              <span className="text-muted">
                {" "}
                ({formatBytes(disk.used_bytes)} of{" "}
                {formatBytes(disk.total_bytes)})
              </span>
            )}
          </p>
        </div>
      )}
      {disk.db_bytes != null && (
        <p className="mt-3 text-sm">Database: {formatBytes(disk.db_bytes)}</p>
      )}
      {disk.top_tables.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-muted">
          {disk.top_tables.map((t) => (
            <li key={t.name} className="flex justify-between gap-2">
              <span className="min-w-0 truncate">{t.name}</span>
              <span>{formatBytes(t.bytes)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
