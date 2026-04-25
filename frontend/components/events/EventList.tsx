'use client';
/**
 * @file components/events/EventList.tsx
 * @brief Vertical list of EventCards grouped by month with sticky headers.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Skeleton, EmptyState } from '@/components/ui';
import { EventCard } from './EventCard';
import { useUpcomingEvents } from '@/hooks/useEvents';
import type { EventItem } from '@/lib/api/events';

function monthKey(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: 'long', year: 'numeric' });
}

function dayLabel(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
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
    const k = monthKey(ev.starts_at);
    (groups[k] ??= []).push(ev);
  }

  return (
    <Stack spacing={0} sx={{ display: 'flex', flexDirection: 'column' }}>
      {Object.entries(groups).map(([month, items]) => (
        <React.Fragment key={month}>
          <Typography
            level="title-sm"
            component="h3"
            sx={{
              position: 'sticky',
              top: 0,
              zIndex: 10,
              py: 1,
              px: 2,
              bgcolor: 'background.surface',
              borderBottom: '1px solid',
              borderColor: 'divider',
              fontWeight: 'bold',
              textTransform: 'uppercase',
              fontSize: '0.875rem',
              letterSpacing: '0.05em',
              color: 'text.secondary',
            }}
          >
            {month}
          </Typography>
          <Stack spacing={1.5} sx={{ px: 2, py: 2 }}>
            {items.map((ev) => (
              <EventCard key={ev.id} event={ev} />
            ))}
          </Stack>
        </React.Fragment>
      ))}
    </Stack>
  );
}

export default EventList;
