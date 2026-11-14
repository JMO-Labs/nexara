/**
 * @file components/admin/AIMetricsChart.tsx
 * @brief Dependency-free SVG line chart of the last 7 days of AI spend.
 */
import type { AIMetrics } from "@/lib/api/adminAI";

export const usd = (cents: number) => `$${(cents / 100).toFixed(2)}`;

/**
 * @brief 7-day spend line chart with an accessible text summary.
 * @param days date/cents series
 * @return svg figure
 */
export function AIMetricsChart({ days }: { days: AIMetrics["last_7_days"] }) {
  const W = 320;
  const H = 120;
  const max = Math.max(1, ...days.map((d) => d.cents));
  const step = days.length > 1 ? W / (days.length - 1) : 0;
  const pts = days.map((d, i) => [i * step, H - (d.cents / max) * (H - 8) - 4]);
  const label = `Line chart of AI spend over the last 7 days: ${days
    .map((d) => `${d.date} ${usd(d.cents)}`)
    .join(", ")}`;
  return (
    <figure>
      <svg
        role="img"
        aria-label={label}
        viewBox={`0 0 ${W} ${H}`}
        className="h-32 w-full overflow-visible"
      >
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="text-accent"
          points={pts.map((p) => p.join(",")).join(" ")}
        />
        {pts.map(([x, y], i) => (
          <circle key={days[i].date} cx={x} cy={y} r="3" fill="currentColor" />
        ))}
      </svg>
      <figcaption className="mt-1 flex justify-between text-xs text-muted">
        <span>{days[0]?.date}</span>
        <span>{days[days.length - 1]?.date}</span>
      </figcaption>
    </figure>
  );
}
