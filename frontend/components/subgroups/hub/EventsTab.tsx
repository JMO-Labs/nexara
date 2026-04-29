'use client';
/**
 * @file components/subgroups/hub/EventsTab.tsx
 * @brief Events tab: month calendar + day rail scoped to the subgroup.
 *        Mirrors the calendar page layout (MonthCalendarLarge + EventRail)
 *        but locked to this group's events. Members get a "New event" button.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import {
  endOfMonth,
  isSameDay,
  parseISO,
  startOfDay,
  startOfMonth,
} from 'date-fns';
import { Button } from '@/components/ui';
import { MonthCalendarLarge } from '@/components/events/MonthCalendarLarge';
import { EventRail } from '@/components/events/EventRail';
import { EventDetailPanel } from '@/components/events/EventDetailPanel';
import { EventCreateModal } from '@/components/events/EventCreateModal';
import { useEventsInRange } from '@/hooks/useEvents';
import type { SubgroupDetail } from '@/lib/api/subgroups';
import type { EventItem } from '@/lib/api/events';

export interface EventsTabProps {
  subgroup: SubgroupDetail;
}

export function EventsTab({ subgroup }: EventsTabProps) {
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editEvent, setEditEvent] = React.useState<EventItem | null>(null);
  const [month, setMonth] = React.useState(() => startOfMonth(new Date()));
  const [selectedDay, setSelectedDay] = React.useState<Date | null>(() =>
    startOfDay(new Date()),
  );
  const [selectedEventId, setSelectedEventId] = React.useState<string | null>(
    null,
  );

  const monthStart = React.useMemo(() => startOfMonth(month), [month]);
  const monthEnd = React.useMemo(() => endOfMonth(month), [month]);

  const { data, isLoading } = useEventsInRange(monthStart, monthEnd, subgroup.id);
  const events = React.useMemo(() => data?.items ?? [], [data?.items]);

  const subgroupNames = React.useMemo(
    () => new Map<string, string>([[subgroup.id, subgroup.name]]),
    [subgroup.id, subgroup.name],
  );

  const railEvents = React.useMemo(() => {
    if (!selectedDay) return events;
    return events.filter((ev) => {
      const s = startOfDay(parseISO(ev.starts_at));
      const e = startOfDay(parseISO(ev.ends_at));
      return selectedDay >= s && selectedDay <= e;
    });
  }, [events, selectedDay]);

  const selectedEvent = React.useMemo(
    () => events.find((e) => e.id === selectedEventId) ?? null,
    [events, selectedEventId],
  );

  const onSelectDay = (d: Date) => {
    setSelectedDay((prev) => (prev && isSameDay(prev, d) ? null : d));
  };

  const onSelectEvent = (ev: EventItem) => {
    setSelectedEventId(ev.id);
    setSelectedDay(startOfDay(parseISO(ev.starts_at)));
  };

  const wrapperRef = React.useRef<HTMLDivElement | null>(null);
  const canCreate = !!subgroup.my_role;

  return (
    <Box ref={wrapperRef} sx={{ position: 'relative', minHeight: 400 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Box
          sx={{
            fontFamily: 'var(--font-display)',
            fontSize: 14,
            textTransform: 'uppercase',
            letterSpacing: '0.16em',
            fontWeight: 700,
            color: 'text.secondary',
          }}
        >
          {events.length} {events.length === 1 ? 'event' : 'events'} this month
        </Box>
        {canCreate && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            New event
          </Button>
        )}
      </Stack>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', lg: 'minmax(0, 1fr) 320px' },
          gap: 2,
          alignItems: 'start',
        }}
      >
        <Box
          sx={{
            minWidth: 0,
            opacity: isLoading ? 0.6 : 1,
            transition: 'opacity 200ms',
          }}
        >
          <MonthCalendarLarge
            events={events}
            month={month}
            selectedDay={selectedDay}
            selectedEventId={selectedEventId}
            subgroupNames={subgroupNames}
            onSelectDay={onSelectDay}
            onSelectEvent={onSelectEvent}
          />
          <Stack
            direction="row"
            spacing={1}
            sx={{ mt: 1, justifyContent: 'center' }}
          >
            <Button
              size="sm"
              variant="plain"
              onClick={() =>
                setMonth((m) => startOfMonth(new Date(m.getFullYear(), m.getMonth() - 1, 1)))
              }
            >
              ← Prev
            </Button>
            <Button
              size="sm"
              variant="plain"
              onClick={() => setMonth(startOfMonth(new Date()))}
            >
              Today
            </Button>
            <Button
              size="sm"
              variant="plain"
              onClick={() =>
                setMonth((m) => startOfMonth(new Date(m.getFullYear(), m.getMonth() + 1, 1)))
              }
            >
              Next →
            </Button>
          </Stack>
        </Box>

        <Box
          sx={{
            position: { lg: 'sticky' },
            top: { lg: 16 },
            height: { xs: 'auto', lg: 'calc(100vh - 200px)' },
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 'sm',
            backgroundColor: 'background.body',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              px: 2,
              py: 1.25,
              borderBottom: '1px solid',
              borderColor: 'divider',
              fontFamily: 'var(--font-display)',
              fontSize: 13,
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

      <EventCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        defaultSubgroupId={subgroup.id}
      />
      <EventCreateModal
        open={!!editEvent}
        event={editEvent}
        onClose={() => setEditEvent(null)}
      />
    </Box>
  );
}

export default EventsTab;
