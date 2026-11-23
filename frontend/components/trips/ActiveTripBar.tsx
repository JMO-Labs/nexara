"use client";
/**
 * @file components/trips/ActiveTripBar.tsx
 * @brief Strip under the top bar while the viewer is traveling: label,
 *        expected time, "Made it", extend and cancel. Renders nothing otherwise.
 */
import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Route } from "lucide-react";
import { Button } from "@/components/ui";
import { TRIPS_KEY, useActiveTrip } from "@/hooks/useTrips";
import { arriveTrip, cancelTrip } from "@/lib/api/trips";
import { ExtendTripDialog } from "./ExtendTripDialog";
import { fmtTime } from "./tripTime";

/** @return the bar, or null when there is no active trip */
export function ActiveTripBar() {
  const qc = useQueryClient();
  const { data: trip } = useActiveTrip();
  const [extend, setExtend] = React.useState(false);
  const done = {
    onSuccess: () => qc.invalidateQueries({ queryKey: TRIPS_KEY }),
  };
  const arrive = useMutation({
    mutationFn: (id: string) => arriveTrip(id),
    ...done,
  });
  const cancel = useMutation({
    mutationFn: (id: string) => cancelTrip(id),
    ...done,
  });
  if (!trip) return null;
  const late =
    trip.alerted_at != null || Date.parse(trip.expected_at) < Date.now();
  return (
    <section
      aria-label="Active trip"
      className="glass-item mx-4 mb-2 flex flex-wrap items-center gap-2 rounded-2xl px-4 py-2 md:mx-8"
    >
      <Route aria-hidden className="size-4 shrink-0" />
      <p className="min-w-0 flex-1 text-sm">
        <span className="font-medium">{trip.label}</span>
        <span className="text-[var(--nx-muted)]">
          {" "}
          · expected {fmtTime(trip.expected_at)}
        </span>
        {late && (
          <span className="text-danger font-medium"> · Running late</span>
        )}
      </p>
      <Button
        size="sm"
        loading={arrive.isPending}
        onClick={() => arrive.mutate(trip.id)}
      >
        Made it
      </Button>
      <Button size="sm" variant="ghost" onClick={() => setExtend(true)}>
        Extend
      </Button>
      <Button
        size="sm"
        variant="ghost"
        loading={cancel.isPending}
        onClick={() => cancel.mutate(trip.id)}
      >
        Cancel trip
      </Button>
      <ExtendTripDialog
        tripId={trip.id}
        open={extend}
        onClose={() => setExtend(false)}
      />
    </section>
  );
}
