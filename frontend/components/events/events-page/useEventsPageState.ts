"use client";
/**
 * @file components/events/events-page/useEventsPageState.ts
 * @brief State, data fetching and derived lists for the events page.
 */
import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  addDays,
  endOfMonth,
  isSameDay,
  parseISO,
  startOfDay,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import {
  VIEWS,
  type CalendarView,
} from "@/components/events/CalendarViewSwitcher";
import type { CalendarSourceId } from "@/components/events/CalendarFilterBar";
import { useEventsInRange } from "@/hooks/useEvents";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useCalendars } from "@/hooks/useCalendars";
import type { EventItem } from "@/lib/api/events";

/**
 * @brief All state and derived data for the events page.
 * @return state bag consumed by EventsPage
 */
export function useEventsPageState() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const raw = searchParams.get("view");
  // Unknown ?view= values fall back to month instead of rendering "undefined".
  const viewParam = (VIEWS as readonly string[]).includes(raw ?? "")
    ? (raw as CalendarView)
    : null;
  const [view, setViewLocal] = React.useState<CalendarView>(
    () => viewParam ?? "month",
  );

  const setView = (newView: CalendarView) => {
    setViewLocal(newView);
    const newParams = new URLSearchParams(searchParams);
    newParams.set("view", newView);
    router.push(`?${newParams.toString()}`);
  };

  const [month, setMonth] = React.useState(() => startOfMonth(new Date()));
  const [weekStart, setWeekStart] = React.useState(() =>
    startOfWeek(new Date(), { weekStartsOn: 0 }),
  );
  const [selectedDay, setSelectedDay] = React.useState<Date | null>(() =>
    startOfDay(new Date()),
  );
  const [selectedEventId, setSelectedEventId] = React.useState<string | null>(
    null,
  );

  const monthStart = React.useMemo(() => startOfMonth(month), [month]);
  const monthEnd = React.useMemo(() => endOfMonth(month), [month]);

  const fetchStart = React.useMemo(() => {
    if (view === "week") return weekStart;
    if (view === "day") return selectedDay ?? startOfDay(new Date());
    return monthStart;
  }, [view, weekStart, selectedDay, monthStart]);

  const fetchEnd = React.useMemo(() => {
    if (view === "week") return addDays(weekStart, 7);
    if (view === "day")
      return addDays(selectedDay ?? startOfDay(new Date()), 1);
    return monthEnd;
  }, [view, weekStart, selectedDay, monthEnd]);

  const { data, isLoading, isError, refetch } = useEventsInRange(
    fetchStart,
    fetchEnd,
  );
  const { data: subgroups } = useSubgroupList();
  const { data: calendars } = useCalendars();
  const calendarList = React.useMemo(() => calendars ?? [], [calendars]);

  const [selectedSources, setSelectedSources] = React.useState<
    CalendarSourceId[]
  >([]);
  const knownIdsRef = React.useRef<Set<string>>(new Set());

  // Auto-include newly discovered calendars (default: all on).
  React.useEffect(() => {
    const known = knownIdsRef.current;
    const currentIds = calendarList.map((c) => c.id);
    const additions = currentIds.filter((id) => !known.has(id));
    const removals = [...known].filter((id) => !currentIds.includes(id));
    if (additions.length === 0 && removals.length === 0) return;
    additions.forEach((id) => known.add(id));
    removals.forEach((id) => known.delete(id));
    setSelectedSources((prev) => {
      const next = prev.filter((id) => !removals.includes(id));
      for (const id of additions) if (!next.includes(id)) next.push(id);
      return next;
    });
  }, [calendarList]);

  const filtered = React.useMemo(() => {
    const set = new Set(selectedSources);
    return (data?.items ?? []).filter((ev) =>
      ev.calendar_id ? set.has(ev.calendar_id) : true,
    );
  }, [data?.items, selectedSources]);

  const subgroupNames = React.useMemo(() => {
    const m = new Map<string, string>();
    for (const sg of subgroups ?? []) m.set(sg.id, sg.name);
    return m;
  }, [subgroups]);

  const railEvents = React.useMemo(() => {
    if (!selectedDay) return filtered;
    return filtered.filter((ev) => {
      const s = startOfDay(parseISO(ev.starts_at));
      const e = startOfDay(parseISO(ev.ends_at));
      return selectedDay >= s && selectedDay <= e;
    });
  }, [filtered, selectedDay]);

  const selectedEvent = React.useMemo(
    () => filtered.find((e) => e.id === selectedEventId) ?? null,
    [filtered, selectedEventId],
  );

  const nextEvent = React.useMemo(() => {
    const now = new Date();
    return (
      filtered
        .filter((e) => parseISO(e.starts_at) > now)
        .sort(
          (a, b) =>
            parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
        )[0] ?? null
    );
  }, [filtered]);

  // Clear selections that fell out of range; deferred to avoid cascading renders.
  React.useEffect(() => {
    const isEventValid =
      !selectedEventId || filtered.some((e) => e.id === selectedEventId);
    const isDayValid =
      !selectedDay || (selectedDay >= monthStart && selectedDay <= monthEnd);
    const updates: Array<() => void> = [];
    if (!isEventValid) updates.push(() => setSelectedEventId(null));
    if (!isDayValid) updates.push(() => setSelectedDay(null));
    if (updates.length > 0) {
      const timeoutId = setTimeout(() => updates.forEach((u) => u()), 0);
      return () => clearTimeout(timeoutId);
    }
  }, [filtered, monthStart, monthEnd, selectedEventId, selectedDay]);

  const onSelectDay = (d: Date) =>
    setSelectedDay((prev) => (prev && isSameDay(prev, d) ? null : d));

  const onSelectEvent = (ev: EventItem) => {
    setSelectedEventId(ev.id);
    setSelectedDay(startOfDay(parseISO(ev.starts_at)));
  };

  return {
    view,
    setView,
    month,
    setMonth,
    weekStart,
    setWeekStart,
    selectedDay,
    setSelectedDay,
    selectedEventId,
    setSelectedEventId,
    selectedSources,
    setSelectedSources,
    calendarList,
    isLoading,
    isError,
    refetch,
    filtered,
    subgroupNames,
    railEvents,
    selectedEvent,
    nextEvent,
    onSelectDay,
    onSelectEvent,
  };
}
