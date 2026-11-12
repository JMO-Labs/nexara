"use client";
/**
 * @file components/events/EventCreateModal.tsx
 * @brief Form modal for creating or editing an event. Pass `event` to switch
 *        into edit mode (prefills fields, calls updateEvent on submit).
 */
import * as React from "react";
import {
  Modal,
  Input,
  Textarea,
  Button,
  ScopeSelect,
  type ScopeValue,
} from "@/components/ui";
import { useCreateEvent, useUpdateEvent } from "@/hooks/useEvents";
import { useCalendars } from "@/hooks/useCalendars";
import type { ContributionSlot, EventItem } from "@/lib/api/events";
import { LocationField } from "./event-form/LocationField";
import { ColorField } from "./event-form/ColorField";
import {
  ContributionSlotsField,
  isValidQuantity,
} from "./event-form/ContributionSlotsField";
import {
  DateTimeFields,
  type DateTimeValue,
} from "./event-form/DateTimeFields";
import {
  DEFAULT_END_TIME,
  DEFAULT_START_TIME,
  composeIso,
  splitLocal,
  todayDate,
} from "./event-form/time";

export interface EventCreateModalProps {
  open: boolean;
  onClose: () => void;
  /** When provided, modal switches to edit mode. */
  event?: EventItem | null;
  /** When provided in create mode (no event), pre-fills subgroup and visibility. */
  defaultSubgroupId?: string | null;
}

/**
 * @brief Create/edit event modal.
 * @param props see EventCreateModalProps
 * @return modal element
 */
export function EventCreateModal({
  open,
  onClose,
  event,
  defaultSubgroupId,
}: EventCreateModalProps) {
  const create = useCreateEvent();
  const update = useUpdateEvent(event?.id ?? "");
  const isEdit = !!event;

  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [location, setLocation] = React.useState("");
  const [coords, setCoords] = React.useState<{
    lat: number;
    lon: number;
  } | null>(null);
  const [when, setWhen] = React.useState<DateTimeValue>({
    startDate: "",
    startTime: DEFAULT_START_TIME,
    endDate: "",
    endTime: DEFAULT_END_TIME,
    allDay: false,
  });
  const [scope, setScope] = React.useState<ScopeValue>({
    visibility: "community",
    subgroup_id: null,
  });
  const [color, setColor] = React.useState<string | null>(null);
  const [slots, setSlots] = React.useState<ContributionSlot[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  const { data: calendars } = useCalendars();
  const myGroups = React.useMemo(
    () =>
      (calendars ?? [])
        .filter((c) => c.kind === "subgroup" && c.subgroup_id)
        .map((c) => ({ id: c.subgroup_id as string, name: c.name })),
    [calendars],
  );

  React.useEffect(() => {
    if (!open) return;
    setError(null);
    if (event) {
      const s = splitLocal(event.starts_at);
      const e = splitLocal(event.ends_at);
      setTitle(event.title);
      setDescription(event.description ?? "");
      setLocation(event.location ?? "");
      setCoords(
        event.latitude != null && event.longitude != null
          ? { lat: event.latitude, lon: event.longitude }
          : null,
      );
      setWhen({
        startDate: s.date,
        startTime: event.is_all_day ? DEFAULT_START_TIME : s.time,
        endDate: e.date,
        endTime: event.is_all_day ? DEFAULT_END_TIME : e.time,
        allDay: event.is_all_day,
      });
      setScope({
        visibility: event.visibility as ScopeValue["visibility"],
        subgroup_id: event.subgroup_id ?? null,
      });
      setColor(event.color);
      setSlots(event.contribution_slots ?? []);
    } else {
      const today = todayDate();
      setTitle("");
      setDescription("");
      setLocation("");
      setCoords(null);
      setWhen({
        startDate: today,
        startTime: DEFAULT_START_TIME,
        endDate: today,
        endTime: DEFAULT_END_TIME,
        allDay: false,
      });
      setScope({
        visibility: defaultSubgroupId ? "subgroup" : "community",
        subgroup_id: defaultSubgroupId ?? null,
      });
      setColor(null);
      setSlots([]);
    }
  }, [open, event, defaultSubgroupId]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (scope.visibility === "subgroup" && !scope.subgroup_id) {
      setError("Choose a group to share with.");
      return;
    }
    if (
      slots.some((s) => !s.title.trim() || !isValidQuantity(s.quantity_needed))
    ) {
      setError("Each slot needs a title and a whole quantity of at least 1.");
      return;
    }
    setError(null);
    const body = {
      title,
      description: description || null,
      location: location || null,
      starts_at: composeIso(
        when.startDate,
        when.allDay ? "00:00" : when.startTime,
      ),
      ends_at: composeIso(when.endDate, when.allDay ? "23:59" : when.endTime),
      is_all_day: when.allDay,
      visibility: scope.visibility,
      subgroup_id: scope.visibility === "subgroup" ? scope.subgroup_id : null,
      color,
      latitude: coords?.lat ?? null,
      longitude: coords?.lon ?? null,
      contribution_slots: slots,
    };
    if (isEdit) await update.mutateAsync(body);
    else await create.mutateAsync(body);
    onClose();
  };

  const pending = isEdit ? update.isPending : create.isPending;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Edit event" : "New event"}
    >
      <form className="flex flex-col gap-4" onSubmit={submit}>
        <Input
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <Textarea
          label="Description"
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <LocationField
          value={location}
          onChange={(label, c) => {
            setLocation(label);
            setCoords(c);
          }}
        />
        <DateTimeFields value={when} onChange={setWhen} />
        {!defaultSubgroupId && (
          <ScopeSelect value={scope} onChange={setScope} subgroups={myGroups} />
        )}
        <ColorField value={color} onChange={setColor} />
        <ContributionSlotsField value={slots} onChange={setSlots} />
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pending}>
            {isEdit ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default EventCreateModal;
