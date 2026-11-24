"use client";
/**
 * @file components/home/CountdownStrip.tsx
 * @brief Home strip of followed countdowns (soonest first, max 6).
 */
import Link from "next/link";
import { useFollowing } from "@/hooks/useCountdowns";
import { daysUntil } from "@/lib/api/countdowns";

const MAX = 6;

/**
 * @brief Followed-countdown chips; renders nothing when none.
 * @return strip or null
 */
export function CountdownStrip() {
  const { data } = useFollowing();
  if (!data?.length) return null;
  const items = data
    .map((c) => ({ c, d: daysUntil(c.next_date) }))
    .sort((a, b) => a.d - b.d)
    .slice(0, MAX);
  return (
    <section
      aria-label="Countdowns"
      className="mb-2.5 flex items-center gap-2 md:mb-[18px]"
    >
      <ul className="m-0 flex min-w-0 flex-1 snap-x list-none gap-2 overflow-x-auto p-0 pb-1">
        {items.map(({ c, d }) => (
          <li key={c.id} className="shrink-0 snap-start">
            <Link
              data-testid="countdown-chip"
              href={`/app/countdowns/${c.id}`}
              className={`border-border bg-surface flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${
                d === 0 ? "ring-accent font-bold ring-2" : ""
              }`}
            >
              {c.emoji ? <span aria-hidden>{c.emoji}</span> : null}
              <span className="font-semibold">
                {d === 0 ? "Today!" : d > 0 ? `${d}d` : `${-d}d ago`}
              </span>
              <span className="max-w-40 truncate">{c.title}</span>
            </Link>
          </li>
        ))}
      </ul>
      <Link
        href="/app/countdowns"
        className="text-accent shrink-0 text-sm font-medium whitespace-nowrap hover:underline"
      >
        See all
      </Link>
    </section>
  );
}
