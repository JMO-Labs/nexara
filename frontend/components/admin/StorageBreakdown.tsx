/**
 * @file components/admin/StorageBreakdown.tsx
 * @brief Stacked bar + legend of storage by category with byte counts and %.
 */
import { formatBytes } from "@/lib/formatBytes";

const LABELS: Record<string, string> = {
  images: "Images",
  videos: "Videos",
  thumbnails: "Thumbnails",
  other: "Other media",
  db: "Database",
};
// Distinct fills; each legend row also carries text so color is not the only cue.
const FILLS = ["#6d4fd6", "#1f8a70", "#c27a12", "#8a8f98", "#c2410c"];

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
  let offset = 0;
  return (
    <div className="flex flex-col gap-3">
      <svg
        viewBox="0 0 100 10"
        role="img"
        aria-label="Category breakdown"
        className="h-6 w-full"
        preserveAspectRatio="none"
      >
        {total > 0 &&
          entries.map(([k, v], i) => {
            const w = (v / total) * 100;
            const rect = (
              <rect
                key={k}
                x={offset}
                y={0}
                width={w}
                height={10}
                fill={FILLS[i % FILLS.length]}
              />
            );
            offset += w;
            return rect;
          })}
      </svg>
      <ul className="flex flex-col gap-1 text-sm">
        {entries.map(([k, v], i) => (
          <li key={k} className="flex items-center gap-2">
            <span
              aria-hidden
              className="size-3 rounded-sm"
              style={{ background: FILLS[i % FILLS.length] }}
            />
            <span className="flex-1">{LABELS[k] ?? k}</span>
            <span>{formatBytes(v)}</span>
            <span className="w-14 text-right text-muted">
              {total > 0 ? ((v / total) * 100).toFixed(1) : "0.0"}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
