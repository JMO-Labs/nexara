'use client';
/**
 * @file components/events/EventList.tsx
 * @brief Vertical list of EventCards grouped by date header.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Skeleton, EmptyState } from '@/components/ui';
import { EventCard } from './EventCard';
import { useUpcomingEvents } from '@/hooks/useEvents';
import type { EventItem } from '@/lib/api/events';

function dayKey(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
}

export function EventList() {
  const { data, isLoading, error } = useUpcomingEvents(60);

  if (isLoading) {
    return (
      <Stack spacing={1.5}>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={140} />
        ))}
      </Stack>
    );
  }
  if (error) return <EmptyState title="Couldn't load events" description={String(error)} />;
  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No upcoming events"
        description="Once events are scheduled they'll appear here."
      />
    );
  }

  const groups: Record<string, EventItem[]> = {};
  for (const ev of data.items) {
    const k = dayKey(ev.starts_at);
    (groups[k] ??= []).push(ev);
  }

  return (
    <Stack spacing={3}>
      {Object.entries(groups).map(([k, items]) => (
        <Stack key={k} spacing={1.5}>
          <Typography
            level="title-sm"
            sx={{
              fontFamily: 'var(--font-display)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'text.tertiary',
            }}
          >
            {k}
          </Typography>
          {items.map((ev) => (
            <EventCard key={ev.id} event={ev} />
          ))}
        </Stack>
      ))}
    </Stack>
  );
}

export default EventList;
