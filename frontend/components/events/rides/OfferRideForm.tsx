"use client";
/**
 * @file components/events/rides/OfferRideForm.tsx
 * @brief Inline form to offer a ride or ask for one.
 */
import { useState } from "react";
import { Button, Input } from "@/components/ui";
import type { RideCreate } from "@/lib/api/rides";

/**
 * @brief Form for an offer (seats available) or request (seats needed).
 * @param kind "offer" or "request"
 * @param pending submit in flight
 * @param onSubmit receives the body (depart_at converted to UTC ISO)
 * @param onCancel close the form
 * @return form element
 */
export function OfferRideForm({
  kind,
  pending,
  onSubmit,
  onCancel,
}: {
  kind: "offer" | "request";
  pending: boolean;
  onSubmit: (body: RideCreate) => void;
  onCancel: () => void;
}) {
  const [seats, setSeats] = useState(kind === "offer" ? 3 : 1);
  const [origin, setOrigin] = useState("");
  const [leave, setLeave] = useState("");
  const [note, setNote] = useState("");
  const offer = kind === "offer";
  return (
    <form
      className="mt-2 flex flex-col gap-2 rounded-lg border border-ink/15 p-3"
      aria-label={offer ? "Offer a ride" : "Ask for a ride"}
      onSubmit={(e) => {
        e.preventDefault();
        const d = leave ? new Date(leave) : null;
        onSubmit({
          seats,
          origin: origin.trim(),
          depart_at: d && !isNaN(d.getTime()) ? d.toISOString() : null,
          note: note.trim(),
        });
      }}
    >
      <Input
        label={offer ? "Seats available" : "Seats needed"}
        type="number"
        min={1}
        max={8}
        required
        value={seats}
        onChange={(e) => setSeats(Number(e.target.value))}
      />
      <Input
        label="Leaving from"
        maxLength={120}
        value={origin}
        onChange={(e) => setOrigin(e.target.value)}
      />
      <Input
        label="Leave time (your local time)"
        type="datetime-local"
        value={leave}
        onChange={(e) => setLeave(e.target.value)}
      />
      <Input
        label="Note"
        maxLength={200}
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <div className="flex gap-2">
        <Button type="submit" size="sm" loading={pending}>
          {offer ? "Offer ride" : "Ask for a ride"}
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
