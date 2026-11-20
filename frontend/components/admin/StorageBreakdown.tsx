/**
 * @file components/admin/StorageBreakdown.tsx
 * @brief Stacked bar + legend of storage by category with byte counts and %.
 */
import { formatBytes } from "@/lib/formatBytes";
import { GROUP_PALETTE } from "@/lib/groupColor";

const LABELS: Record<string, string> = {
  images: "Images",
  videos: "Videos",
  thumbnails: "Thumbnails",
  other: "Other media",
  db: "Database",
};
// Brand series; each legend row also carries text so color is not the only cue.
const fill = (i: number) => GROUP_PALETTE[i % GROUP_PALETTE.length];

/**
 * @brief Category breakdown chart.
 * @param categories Map of category key to bytes.
 */
export function StorageBreakdown({
  categories,
}: {
  categories: Record<string, number>;
}) {
  const entries = Object.entries(categories);
  const total = entries.reduce((s, [, v]) => s + v, 0);
  const pct = (v: number) => (total > 0 ? (v / total) * 100 : 0);
  return (
    <div className="flex flex-col gap-3">
      <div
        role="img"
        aria-label="Category breakdown"
        className="flex h-3 w-full overflow-hidden rounded-full bg-ink/10"
      >
        {entries.map(([k, v], i) => (
          <span
            key={k}
            className="h-full"
            style={{ width: `${pct(v)}%`, background: fill(i) }}
          />
        ))}
      </div>
      <ul className="flex flex-col gap-1 text-sm">
        {entries.map(([k, v], i) => (
          <li key={k} className="flex items-center gap-2">
            <span
              aria-hidden
              className="size-3 rounded-full"
              style={{ background: fill(i) }}
            />
            <span className="flex-1">{LABELS[k] ?? k}</span>
            <span>{formatBytes(v)}</span>
            <span className="w-14 text-right text-muted">
              {pct(v).toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
