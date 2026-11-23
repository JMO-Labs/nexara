"use client";
/**
 * @file components/trips/WatchingChips.tsx
 * @brief Home People tile chips: travelers the viewer is watching and when
 *        they expect to arrive. Renders nothing when there are none.
 */
import { Route } from "lucide-react";
import { useWatchingTrips } from "@/hooks/useTrips";
import { fmtTime } from "./tripTime";

/** @return list of chips or null */
export function WatchingChips() {
  const { data: trips = [] } = useWatchingTrips();
  if (trips.length === 0) return null;
  return (
    <div>
      <p className="mb-2 text-sm text-[var(--nx-muted)]">You are watching</p>
      <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
        {trips.map((t) => {
          const late = t.alerted_at != null;
          return (
            <li
              key={t.id}
              className="glass-item flex items-center gap-2 rounded-full px-3 py-1 text-sm"
            >
              <Route aria-hidden className="size-3.5" />
              <span>
                {t.traveler.display_name.split(" ")[0]} to {t.label}
                <span className="text-[var(--nx-muted)]">
                  {" "}
                  · {fmtTime(t.expected_at)}
                </span>
                {late && (
                  <span className="text-danger font-medium"> · Overdue</span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
