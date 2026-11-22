"use client";
/**
 * @file components/wishlists/wizard/ShipToField.tsx
 * @brief "Ship gifts to": nobody, a person (their shared profile address),
 *        an event's location (both kept up to date) or a typed address.
 */
import { CalendarDays, MapPin, PenLine, User } from "lucide-react";
import { Textarea } from "@/components/ui";
import { Segmented } from "@/components/ui/page";
import { useMembersList } from "@/hooks/useMembersList";
import { useUpcomingEvents } from "@/hooks/useEvents";
import { useSession } from "@/stores/session";
import { Field, selectCls } from "./fields";
import type { Draft } from "./draft";

/** @brief Shipping address picker for the details step. */
export function ShipToField({
  d,
  set,
}: {
  d: Draft;
  set: (p: Partial<Draft>) => void;
}) {
  const me = useSession((s) => s.user);
  const { data: members = [] } = useMembersList();
  const { data: upcoming } = useUpcomingEvents(365);
  const events = upcoming?.items ?? [];
  const people = [
    ...(me ? [{ id: me.id, label: "Me" }] : []),
    ...members
      .filter((m) => m.id !== me?.id)
      .map((m) => ({ id: m.id, label: m.display_name })),
  ];
  return (
    <section className="flex flex-col gap-3" aria-label="Shipping">
      <Segmented
        label="Ship gifts to"
        value={d.ship_mode}
        onChange={(ship_mode) => set({ ship_mode })}
        options={[
          { value: "none", label: "No address", icon: MapPin },
          { value: "user", label: "A person", icon: User },
          { value: "event", label: "An event", icon: CalendarDays },
          { value: "text", label: "Type it", icon: PenLine },
        ]}
      />
      {d.ship_mode === "user" && (
        <Field
          label="Person"
          hint="Uses the address on their profile and follows it if they move. Works only if they share their address with the community."
        >
          <select
            className={selectCls}
            value={d.ship_to_user_id}
            onChange={(e) => set({ ship_to_user_id: e.target.value })}
          >
            <option value="">Choose someone</option>
            {people.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </Field>
      )}
      {d.ship_mode === "event" && (
        <Field
          label="Event"
          hint="Uses the event's location and follows it if it changes. People who can't see the event won't see the address."
        >
          <select
            className={selectCls}
            value={d.ship_to_event_id}
            onChange={(e) => set({ ship_to_event_id: e.target.value })}
          >
            <option value="">Choose an event</option>
            {events.map((ev) => (
              <option key={ev.id} value={ev.id}>
                {ev.title}
                {ev.location ? ` (${ev.location})` : " (no location yet)"}
              </option>
            ))}
          </select>
        </Field>
      )}
      {d.ship_mode === "text" && (
        <Field label="Address">
          <Textarea
            rows={3}
            maxLength={500}
            placeholder={"Name\nStreet\nCity, State ZIP"}
            value={d.ship_to_text}
            onChange={(e) => set({ ship_to_text: e.target.value })}
          />
        </Field>
      )}
      {d.ship_mode !== "none" && (
        <span className="text-xs text-muted">
          Everyone who can see this list sees the address.
        </span>
      )}
    </section>
  );
}
