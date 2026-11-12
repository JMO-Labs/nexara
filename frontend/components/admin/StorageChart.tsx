/**
 * @file components/admin/StorageChart.tsx
 * @brief Dependency-free SVG line chart of total storage over time.
 */
import { formatBytes } from "@/lib/formatBytes";
import type { StorageSnapshot } from "@/lib/api/adminStorage";

const W = 600;
const H = 220;
const PAD = { l: 8, r: 8, t: 12, b: 24 };

/**
 * @brief Line chart of snapshots (X = date, Y = total_bytes).
 * @param data Snapshots, oldest first.
 */
export function StorageChart({ data }: { data: StorageSnapshot[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted">No snapshots yet.</p>;
  }
  const max = Math.max(...data.map((d) => d.total_bytes), 1);
  const x = (i: number) =>
    PAD.l +
    (data.length === 1
      ? (W - PAD.l - PAD.r) / 2
      : (i / (data.length - 1)) * (W - PAD.l - PAD.r));
  const y = (v: number) => PAD.t + (1 - v / max) * (H - PAD.t - PAD.b);
  const points = data.map((d, i) => `${x(i)},${y(d.total_bytes)}`).join(" ");
  const first = data[0];
  const last = data[data.length - 1];

  return (
    <figure className="w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Storage over time, from ${formatBytes(first.total_bytes)} on ${first.date} to ${formatBytes(last.total_bytes)} on ${last.date}`}
        className="h-auto w-full"
      >
        <line
          x1={PAD.l}
          x2={W - PAD.r}
          y1={H - PAD.b}
          y2={H - PAD.b}
          stroke="currentColor"
          strokeOpacity={0.2}
        />
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          points={points}
        />
        {data.map((d, i) => (
          <circle
            key={d.date}
            cx={x(i)}
            cy={y(d.total_bytes)}
            r={3}
            fill="currentColor"
          >
            <title>{`${d.date}: ${formatBytes(d.total_bytes)}`}</title>
          </circle>
        ))}
        <text x={PAD.l} y={H - 6} fontSize={11} fill="currentColor">
          {first.date}
        </text>
        <text
          x={W - PAD.r}
          y={H - 6}
          fontSize={11}
          textAnchor="end"
          fill="currentColor"
        >
          {last.date}
        </text>
      </svg>
      <figcaption className="sr-only">Peak {formatBytes(max)}</figcaption>
    </figure>
  );
}
