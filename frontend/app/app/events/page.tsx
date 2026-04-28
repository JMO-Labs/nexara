'use client';
/**
 * @file app/app/events/page.tsx
 * @brief Events page. Three-zone editorial layout: large month calendar (left),
 *        sorted day-grouped event rail (right), and a slide-up detail panel
 *        (bottom). Calendar source filter (multi-select grouped dropdown)
 *        controls which calendars contribute events; all three zones stay
 *        in sync with the current month + selected event/day.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import { endOfMonth, isSameDay, parseISO, startOfDay, startOfMonth } from 'date-fns';
import { EventCreateModal } from '@/components/events/EventCreateModal';
import { MonthCalendarLarge } from '@/components/events/MonthCalendarLarge';
import { EventRail } from '@/components/events/EventRail';
import { EventDetailPanel } from '@/components/events/EventDetailPanel';
import { EventCountdown } from '@/components/events/EventCountdown';
import {
  CalendarFilterBar,
  type CalendarSourceId,
} from '@/components/events/CalendarFilterBar';
import { useEventsInRange } from '@/hooks/useEvents';
import { useSubgroupList } from '@/hooks/useSubgroups';
import { useCalendars } from '@/hooks/useCalendars';
import type { EventItem } from '@/lib/api/events';

export default function EventsPage() {
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editEvent, setEditEvent] = React.useState<EventItem | null>(null);
  const [month, setMonth] = React.useState(() => startOfMonth(new Date()));
  const [selectedDay, setSelectedDay] = React.useState<Date | null>(
    () => startOfDay(new Date()),
  );
  const [selectedEventId, setSelectedEventId] = React.useState<string | null>(null);

  const monthStart = React.useMemo(() => startOfMonth(month), [month]);
  const monthEnd = React.useMemo(() => endOfMonth(month), [month]);
  const { data, isLoading } = useEventsInRange(monthStart, monthEnd);
  const { data: subgroups } = useSubgroupList();
  const { data: calendars } = useCalendars();

  const calendarList = React.useMemo(() => calendars ?? [], [calendars]);

  const [selectedSources, setSelectedSources] = React.useState<CalendarSourceId[]>([]);
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

  const allEvents = data?.items ?? [];
  const filtered = React.useMemo(() => {
    const set = new Set(selectedSources);
    return allEvents.filter((ev) => (ev.calendar_id ? set.has(ev.calendar_id) : true));
  }, [allEvents, selectedSources]);

  const subgroupNames = React.useMemo(() => {
    const m = new Map<string, string>();
    for (const sg of subgroups ?? []) m.set(sg.id, sg.name);
    return m;
  }, [subgroups]);

  // Rail filtered to selected day if any
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

  // Find next upcoming event for countdown
  const nextEvent = React.useMemo(() => {
    const now = new Date();
    return filtered
      .filter((e) => parseISO(e.starts_at) > now)
      .sort((a, b) => parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime())[0] ?? null;
  }, [filtered]);

  // If month changes, drop selection that no longer exists
  React.useEffect(() => {
    if (selectedEventId && !filtered.some((e) => e.id === selectedEventId)) {
      setSelectedEventId(null);
    }
    if (selectedDay && (selectedDay < monthStart || selectedDay > monthEnd)) {
      setSelectedDay(null);
    }
  }, [filtered, selectedEventId, selectedDay, monthStart, monthEnd]);

  const onSelectDay = (d: Date) => {
    setSelectedDay((prev) => (prev && isSameDay(prev, d) ? null : d));
  };

  const onSelectEvent = (ev: EventItem) => {
    setSelectedEventId(ev.id);
    setSelectedDay(startOfDay(parseISO(ev.starts_at)));
  };

  const wrapperRef = React.useRef<HTMLDivElement | null>(null);
  const drawerReserve = selectedEvent ? 296 : 0;

  return (
    <Box
      ref={wrapperRef}
      sx={{
        px: { xs: 1.5, md: 2 },
        py: { xs: 2, md: 2.5 },
        pb: { xs: `${drawerReserve + 16}px`, md: `${drawerReserve + 24}px` },
        width: '100%',
        minHeight: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
      }}
    >
      <CalendarFilterBar
        month={month}
        onMonthChange={setMonth}
        selected={selectedSources}
        onSelectedChange={(ids) => {
          setSelectedSources(ids);
          setSelectedEventId(null);
        }}
        calendars={calendarList}
        onCreate={() => setCreateOpen(true)}
      />

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: 'minmax(0, 1fr) 340px' },
          gap: { xs: 2, md: 2 },
          alignItems: 'start',
          flex: 1,
          minHeight: 0,
        }}
      >
        <Box sx={{ minWidth: 0, opacity: isLoading ? 0.6 : 1, transition: 'opacity 200ms' }}>
          <MonthCalendarLarge
            events={filtered}
            month={month}
            selectedDay={selectedDay}
            selectedEventId={selectedEventId}
            subgroupNames={subgroupNames}
            onSelectDay={onSelectDay}
            onSelectEvent={onSelectEvent}
          />
        </Box>

        <Box
          sx={{
            position: { lg: 'sticky' },
            top: { lg: 16 },
            height: { xs: 'auto', lg: 'calc(100vh - 160px)' },
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 'sm',
            backgroundColor: 'background.body',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {nextEvent && <EventCountdown event={nextEvent} key={nextEvent.id} />}
          <Box
            sx={{
              px: 2,
              py: 1.25,
              borderBottom: '1px solid',
              borderColor: 'divider',
              fontFamily: 'var(--font-display)',
              fontSize: 14,
              textTransform: 'uppercase',
              letterSpacing: '0.16em',
              fontWeight: 700,
              color: 'text.secondary',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>{selectedDay ? 'This day' : 'This month'}</span>
            {selectedDay && (
              <Box
                role="button"
                tabIndex={0}
                onClick={() => setSelectedDay(null)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSelectedDay(null);
                  }
                }}
                sx={{
                  cursor: 'pointer',
                  fontSize: 10,
                  letterSpacing: '0.18em',
                  color: 'text.tertiary',
                  '&:hover': { color: 'text.primary' },
                }}
              >
                Clear
              </Box>
            )}
          </Box>
          <Box sx={{ flex: 1, minHeight: 0 }}>
            <EventRail
              events={railEvents}
              selectedDay={selectedDay}
              selectedEventId={selectedEventId}
              subgroupNames={subgroupNames}
              onSelectEvent={onSelectEvent}
            />
          </Box>
        </Box>
      </Box>

      <EventDetailPanel
        containerRef={wrapperRef}
        event={selectedEvent}
        subgroupNames={subgroupNames}
        onClose={() => setSelectedEventId(null)}
        onEdit={(ev) => setEditEvent(ev)}
      />

      <EventCreateModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <EventCreateModal
        open={!!editEvent}
        event={editEvent}
        onClose={() => setEditEvent(null)}
      />
    </Box>
  );
}
