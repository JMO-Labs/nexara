"use client";
/**
 * @file components/trips/ExtendTripDialog.tsx
 * @brief Move the expected arrival time of the active trip.
 */
import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Input, Modal } from "@/components/ui";
import { TRIPS_KEY } from "@/hooks/useTrips";
import { extendTrip } from "@/lib/api/trips";
import { toIso, tripWindow } from "./tripTime";

/**
 * @param tripId active trip id
 * @param open modal visibility
 * @param onClose close handler
 * @return modal dialog
 */
export function ExtendTripDialog({
  tripId,
  open,
  onClose,
}: {
  tripId: string;
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [when, setWhen] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const save = useMutation({
    mutationFn: () => extendTrip(tripId, toIso(when)!),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TRIPS_KEY });
      setWhen("");
      onClose();
    },
    onError: () => setError("Could not update the trip. Please try again."),
  });
  const { min, max } = tripWindow();
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Running late?"
      description="Pick a new arrival time. Your watchers are told again only if you are late for that too."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            loading={save.isPending}
            onClick={() => {
              setError(null);
              if (!toIso(when))
                return setError(
                  "Pick a time between 10 minutes and 3 days away.",
                );
              save.mutate();
            }}
          >
            Update time
          </Button>
        </>
      }
    >
      <Input
        label="New expected arrival (your local time)"
        type="datetime-local"
        min={min}
        max={max}
        value={when}
        onChange={(e) => setWhen(e.target.value)}
      />
      {error && (
        <p role="alert" className="text-danger mt-2 text-sm">
          {error}
        </p>
      )}
    </Modal>
  );
}
