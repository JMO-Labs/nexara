'use client';
/**
 * @file components/events/EventCard.tsx
 * @brief Event tile: title, schedule, location, RSVP row.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Box from '@mui/joy/Box';
import { Card, Markdown } from '@/components/ui';
import { RsvpInline } from './RsvpInline';
import type { EventItem } from '@/lib/api/events';

export interface EventCardProps {
  event: EventItem;
}

function formatRange(starts: string, ends: string, allDay: boolean): string {
  const s = new Date(starts);
  const e = new Date(ends);
  const date = s.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  if (allDay) return `${date} · All day`;
  const t = (d: Date) => d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  return `${date} · ${t(s)} – ${t(e)}`;
}

export function EventCard({ event }: EventCardProps) {
  return (
    <Card>
      <Stack spacing={1}>
        <Typography level="title-md" sx={{ fontFamily: 'var(--font-display)' }}>
          {event.title}
        </Typography>
        <Typography level="body-sm" sx={{ color: 'text.tertiary' }}>
          {formatRange(event.starts_at, event.ends_at, event.is_all_day)}
        </Typography>
        {event.location && (
          <Typography level="body-sm">📍 {event.location}</Typography>
        )}
        {event.description && (
          <Box sx={{ fontSize: '0.875rem' }}>
            <Markdown content={event.description} size="sm" truncate clampLines={4} />
          </Box>
        )}
        <RsvpInline
          eventId={event.id}
          labels={event.rsvp_labels}
          current={event.user_rsvp?.status ?? null}
          counts={event.rsvp_counts}
        />
      </Stack>
    </Card>
  );
}

export default EventCard;
