"use client";
/**
 * @file components/trips/StartTripDialog.tsx
 * @brief Start a trip: label, expected arrival (datetime-local, 10 min to 72 h
 *        ahead) and 1-20 watchers. No location is collected.
 */
import * as React from "react";
import { X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Input, Modal } from "@/components/ui";
import { Field, selectCls } from "@/components/wishlists/wizard/fields";
import { useMembersList } from "@/hooks/useMembersList";
import { TRIPS_KEY } from "@/hooks/useTrips";
import { useSession } from "@/stores/session";
import { startTrip } from "@/lib/api/trips";
import { toIso, tripWindow } from "./tripTime";

/**
 * @param open modal visibility
 * @param onClose close handler
 * @return modal dialog
 */
export function StartTripDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const meId = useSession((s) => s.user?.id);
  const { data: members = [] } = useMembersList();
  const [label, setLabel] = React.useState("");
  const [when, setWhen] = React.useState("");
  const [watchers, setWatchers] = React.useState<string[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const save = useMutation({
    mutationFn: () =>
      startTrip({
        label: label.trim(),
        expected_at: toIso(when)!,
        watcher_ids: watchers,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TRIPS_KEY });
      setLabel("");
      setWhen("");
      setWatchers([]);
      onClose();
    },
    onError: () => setError("Could not start the trip. Please try again."),
  });
  const name = (id: string) =>
    members.find((m) => m.id === id)?.display_name ?? "Someone";

  const submit = () => {
    setError(null);
    if (!label.trim()) return setError("Add where you are going.");
    if (!toIso(when))
      return setError(
        "Pick an arrival time between 10 minutes and 3 days away.",
      );
    if (watchers.length === 0) return setError("Choose who should be told.");
    save.mutate();
  };
  const { min, max } = tripWindow();

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Start a trip"
      description="The people you choose are told when you start, and again if you have not said you made it an hour after your expected time. Your location is never shared."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={save.isPending}>
            Start trip
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Input
          label="Where are you going?"
          maxLength={80}
          value={label}
          onChange={(e) => setLabel(e.target.value)}
        />
        <Input
          label="Expected arrival (your local time)"
          type="datetime-local"
          min={min}
          max={max}
          value={when}
          onChange={(e) => setWhen(e.target.value)}
        />
        <Field label="Who should watch">
          <select
            className={selectCls}
            value=""
            onChange={(e) => {
              const id = e.target.value;
              if (id && watchers.length < 20 && !watchers.includes(id))
                setWatchers([...watchers, id]);
            }}
          >
            <option value="">Add a person</option>
            {members
              .filter((m) => m.id !== meId && !watchers.includes(m.id))
              .map((m) => (
                <option key={m.id} value={m.id}>
                  {m.display_name}
                </option>
              ))}
          </select>
        </Field>
        {watchers.length > 0 && (
          <ul
            aria-label="Watchers"
            className="m-0 flex list-none flex-wrap gap-2 p-0"
          >
            {watchers.map((id) => (
              <li
                key={id}
                className="glass-item flex items-center gap-1 rounded-full py-1 pr-1 pl-3 text-sm"
              >
                {name(id)}
                <button
                  type="button"
                  aria-label={`Remove ${name(id)}`}
                  className="focus-visible:outline-accent rounded-full p-1 focus-visible:outline-2"
                  onClick={() => setWatchers(watchers.filter((w) => w !== id))}
                >
                  <X aria-hidden className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
        {error && (
          <p role="alert" className="text-danger text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
