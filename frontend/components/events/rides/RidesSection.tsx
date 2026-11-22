"use client";
/**
 * @file components/events/rides/RidesSection.tsx
 * @brief "Rides" section on the event detail: offers, requests and forms.
 *        Renders nothing when the `rides` feature is off.
 */
import { useState } from "react";
import { Button } from "@/components/ui";
import { useFeature } from "@/hooks/useFeature";
import { useRideActions, useRides } from "@/hooks/useRides";
import { useSession } from "@/stores/session";
import { ApiError } from "@/lib/api/errors";
import { OfferRideForm } from "./OfferRideForm";
import { RideCard } from "./RideCard";

/**
 * @param eventId event the rides belong to
 * @return section, or null when the feature is off
 */
export function RidesSection({ eventId }: { eventId: string }) {
  const on = useFeature("rides");
  const userId = useSession((s) => s.user?.id);
  const { data: rides = [] } = useRides(eventId, on);
  const act = useRideActions(eventId);
  const [form, setForm] = useState<"offer" | "request" | null>(null);
  if (!on) return null;
  const offers = rides.filter((r) => r.kind === "offer");
  const requests = rides.filter((r) => r.kind === "request");
  const myOpen = offers.filter((r) => r.user_id === userId && r.seats_left > 0);
  const failed = Object.values(act).find((m) => m.isError)?.error;
  const busy = Object.values(act).some((m) => m.isPending);
  const card = (r: (typeof rides)[number]) => (
    <RideCard
      key={r.id}
      ride={r}
      userId={userId}
      myOpenOffers={myOpen}
      busy={busy}
      onJoin={(id) => act.join.mutate(id)}
      onLeave={(id) => act.leave.mutate(id)}
      onCancel={(id) => act.cancel.mutate(id)}
      onAnswer={(requestId, offerId) =>
        act.answer.mutate({ requestId, offerId })
      }
    />
  );
  const done = () => setForm(null);
  return (
    <section className="mt-4" aria-labelledby="rides-h">
      <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
        <h3
          id="rides-h"
          className="text-xs font-semibold tracking-wider text-muted"
        >
          Rides
        </h3>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setForm("offer")}
          >
            Offer a ride
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setForm("request")}
          >
            Need a ride
          </Button>
        </div>
      </div>
      {failed && (
        <p role="alert" className="mb-2 text-sm text-destructive">
          {failed instanceof ApiError ? failed.message : "Something went wrong"}
        </p>
      )}
      {form && (
        <OfferRideForm
          kind={form}
          pending={act.offer.isPending || act.request.isPending}
          onCancel={done}
          onSubmit={(b) =>
            (form === "offer" ? act.offer : act.request).mutate(b, {
              onSuccess: done,
            })
          }
        />
      )}
      {rides.length === 0 && !form && (
        <p className="text-sm text-muted">No rides yet.</p>
      )}
      {offers.length > 0 && (
        <ul aria-label="Ride offers" className="mt-2 flex flex-col gap-2">
          {offers.map(card)}
        </ul>
      )}
      {requests.length > 0 && (
        <ul aria-label="Ride requests" className="mt-2 flex flex-col gap-2">
          {requests.map(card)}
        </ul>
      )}
    </section>
  );
}
