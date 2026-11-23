"use client";
/**
 * @file components/events/rides/RideCard.tsx
 * @brief One ride offer or request with its action buttons.
 */
import { useState } from "react";
import { Button } from "@/components/ui";
import type { Ride } from "@/lib/api/rides";

/** @brief Format a UTC instant in the viewer's local time. */
export function formatDepart(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export interface RideCardProps {
  ride: Ride;
  userId: string | undefined;
  /** the viewer's own offers that still have a seat (for "I can take them") */
  myOpenOffers: Ride[];
  busy: boolean;
  onJoin: (id: string, seats: number) => void;
  onLeave: (id: string) => void;
  onCancel: (id: string) => void;
  onAnswer: (requestId: string, offerId: string) => void;
}

/**
 * @brief Card for one ride.
 * @param p ride, viewer and action callbacks
 * @return list item
 */
export function RideCard({
  ride,
  userId,
  myOpenOffers,
  busy,
  onJoin,
  onLeave,
  onCancel,
  onAnswer,
}: RideCardProps) {
  const [seats, setSeats] = useState(1);
  const mine = ride.user_id === userId;
  const isOffer = ride.kind === "offer";
  const when = formatDepart(ride.depart_at);
  return (
    <li className="flex flex-col gap-1.5 rounded-lg border border-ink/15 px-3 py-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold">
          {mine ? "You" : ride.driver_name}
          {isOffer ? " · driving" : " · needs a ride"}
        </span>
        <span className="tabular-nums text-muted">
          {isOffer
            ? `${ride.seats_left} of ${ride.seats} seats left`
            : `${ride.seats} ${ride.seats === 1 ? "seat" : "seats"} needed`}
        </span>
      </div>
      <p className="text-muted">
        {ride.origin ? `From ${ride.origin}` : "Origin not given"}
        {when && (
          <>
            {" · leaves "}
            <time dateTime={ride.depart_at ?? undefined}>{when}</time>
          </>
        )}
      </p>
      {ride.note && <p>{ride.note}</p>}
      {ride.passengers.length > 0 && (
        <p className="text-muted">
          Riding:{" "}
          {ride.passengers
            .map(
              (p) =>
                `${p.display_name}${p.seats > 1 ? ` (${p.seats} seats)` : ""}`,
            )
            .join(", ")}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        {isOffer && !mine && !ride.joined && ride.seats_left > 0 && (
          <>
            <label className="flex items-center gap-1.5">
              <span>Seats</span>
              <select
                className="h-8 rounded-md border border-ink/20 bg-bg px-2 text-sm"
                value={Math.min(seats, ride.seats_left)}
                onChange={(e) => setSeats(Number(e.target.value))}
              >
                {Array.from({ length: ride.seats_left }, (_, i) => i + 1).map(
                  (n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ),
                )}
              </select>
            </label>
            <Button
              size="sm"
              disabled={busy}
              onClick={() => onJoin(ride.id, Math.min(seats, ride.seats_left))}
            >
              Join ride
            </Button>
          </>
        )}
        {isOffer && !mine && !ride.joined && ride.seats_left === 0 && (
          <Button size="sm" disabled>
            Full
          </Button>
        )}
        {isOffer && ride.joined && (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => onLeave(ride.id)}
          >
            Leave ride
          </Button>
        )}
        {!isOffer &&
          !mine &&
          myOpenOffers.map((o) => (
            <Button
              key={o.id}
              size="sm"
              disabled={busy || o.seats_left < ride.seats}
              onClick={() => onAnswer(ride.id, o.id)}
              aria-label={`I can take ${ride.driver_name} in my ride from ${o.origin || "my place"}`}
            >
              I can take them
            </Button>
          ))}
        {mine && (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={() => onCancel(ride.id)}
          >
            Cancel {isOffer ? "offer" : "request"}
          </Button>
        )}
      </div>
    </li>
  );
}
