"use client";
/**
 * @file hooks/useEvents.ts
 * @brief TanStack hooks for event window queries + CRUD/RSVP mutations.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { qk } from "@/lib/query-keys";
import {
  listEvents,
  getEvent,
  createEvent,
  updateEvent,
  deleteEvent,
  rsvpEvent,
  unrsvpEvent,
  type CreateEventBody,
  type EventItem,
  type ListEventsParams,
} from "@/lib/api/events";

/** Round to start-of-hour so the query key is stable across renders. */
function bucketHour(d: Date): Date {
  const r = new Date(d);
  r.setMinutes(0, 0, 0);
  return r;
}

export function useUpcomingEvents(days = 30, subgroup_id?: string) {
  const now = bucketHour(new Date());
  const end = new Date(now.getTime() + days * 86400_000);
  const start = now.toISOString();
  const endIso = end.toISOString();
  return useQuery({
    queryKey: qk.events.list({ from: start, to: endIso, subgroup_id }),
    queryFn: () => listEvents({ start, end: endIso, limit: 200, subgroup_id }),
    staleTime: 5 * 60_000,
  });
}

export function useEventsInRange(start: Date, end: Date, subgroup_id?: string) {
  const startIso = start.toISOString();
  const endIso = end.toISOString();
  return useQuery({
    queryKey: qk.events.list({ from: startIso, to: endIso, subgroup_id }),
    queryFn: () =>
      listEvents({ start: startIso, end: endIso, limit: 500, subgroup_id }),
    staleTime: 5 * 60_000,
  });
}

export function useEventDetail(id: string | null | undefined) {
  return useQuery({
    queryKey: qk.events.detail(id ?? ""),
    queryFn: () => getEvent(id as string),
    enabled: !!id,
  });
}

function invalidate(qc: ReturnType<typeof useQueryClient>, id?: string) {
  qc.invalidateQueries({ queryKey: qk.events.all() });
  if (id) qc.invalidateQueries({ queryKey: qk.events.detail(id) });
}

export function useCreateEvent() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (body: CreateEventBody) => createEvent(body),
    successKey: "toasts.events.created",
    onSuccess: () => invalidate(qc),
  });
}

export function useUpdateEvent(id: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (body: Partial<CreateEventBody>) => updateEvent(id, body),
    successKey: "toasts.events.updated",
    onSuccess: () => invalidate(qc, id),
  });
}

export function useDeleteEvent() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (id: string) => deleteEvent(id),
    successKey: "toasts.events.cancelled",
    onSuccess: () => invalidate(qc),
  });
}

export function useRsvp(eventId: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: async (status: string | null) => {
      if (status === null) {
        await unrsvpEvent(eventId);
        return null;
      }
      return await rsvpEvent(eventId, status);
    },
    successKey: "toasts.events.rsvp.saved",
    silentSuccess: true,
    onMutate: async (status) => {
      await qc.cancelQueries({ queryKey: qk.events.all() });
      const prevEvent = qc.getQueryData<EventItem>(qk.events.detail(eventId));
      qc.setQueryData<EventItem | undefined>(
        qk.events.detail(eventId),
        (old) => {
          if (!old) return old;
          return {
            ...old,
            user_rsvp: status ? { status } : null,
          };
        },
      );
      return { prevEvent };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prevEvent) {
        qc.setQueryData(qk.events.detail(eventId), ctx.prevEvent);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: qk.events.detail(eventId) });
      qc.invalidateQueries({ queryKey: qk.events.all() });
    },
  });
}
