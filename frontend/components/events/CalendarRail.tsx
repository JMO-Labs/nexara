'use client';
/**
 * @file components/events/CalendarRail.tsx
 * @brief Dashboard right-rail calendar. Month grid with event bars + hover
 *        preview, plus a compact "next up" list below.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Box from '@mui/joy/Box';
import Typography from '@mui/joy/Typography';
import Link from 'next/link';
import {
  endOfMonth,
  format,
  parseISO,
  startOfDay,
  startOfMonth,
} from 'date-fns';
import { Card, EmptyState, Skeleton } from '@/components/ui';
import { useEventsInRange } from '@/hooks/useEvents';
import { MonthCalendar } from './MonthCalendar';

export function CalendarRail() {
  const [month, setMonth] = React.useState(() => startOfMonth(new Date()));
  const rangeStart = React.useMemo(() => startOfMonth(month), [month]);
  const rangeEnd = React.useMemo(() => endOfMonth(month), [month]);
  const { data, isLoading, isError, isFetching } = useEventsInRange(
    rangeStart,
    rangeEnd,
  );

  const events = data?.items ?? [];
  const today = startOfDay(new Date());
  const upcoming = events
    .filter((e) => parseISO(e.ends_at) >= today)
    .sort(
      (a, b) =>
        parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
    )
    .slice(0, 5);

  return (
    <Card sx={{ p: 2, position: 'sticky', top: 0, alignSelf: 'flex-start' }}>
      <Stack spacing={1.5}>
        <Stack direction="row" alignItems="baseline" justifyContent="space-between">
          <Typography level="title-md" sx={{ fontFamily: 'var(--font-display)' }}>
            Calendar
          </Typography>
          <Typography
            component={Link}
            href="/app/events"
            level="body-xs"
            sx={{ textDecoration: 'none' }}
          >
            View all
          </Typography>
        </Stack>

        {isLoading ? (
          <Skeleton height={260} />
        ) : isError ? (
          <Typography level="body-sm" color="danger">
            Couldn’t load events.
          </Typography>
        ) : (
          <MonthCalendar
            events={events}
            month={month}
            onMonthChange={setMonth}
          />
        )}

        <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 1 }}>
          <Typography
            level="body-xs"
            textColor="text.tertiary"
            sx={{ textTransform: 'uppercase', letterSpacing: '0.06em', mb: 0.5 }}
          >
            Next up
          </Typography>
          {isLoading || isFetching ? (
            <Stack spacing={0.5}>
              <Skeleton height={32} />
              <Skeleton height={32} />
            </Stack>
          ) : upcoming.length === 0 ? (
            <EmptyState
              compact
              title="No upcoming events"
              description="Nothing on the calendar for now."
            />
          ) : (
            <Stack spacing={0.5}>
              {upcoming.map((ev) => (
                <Box
                  key={ev.id}
                  component={Link}
                  href={`/app/events?focus=${ev.id}`}
                  sx={{
                    display: 'block',
                    textDecoration: 'none',
                    color: 'inherit',
                    p: 0.75,
                    borderRadius: 'sm',
                    borderLeft: '3px solid',
                    borderColor: 'primary.solidBg',
                    backgroundColor: 'background.level1',
                    '&:hover': { backgroundColor: 'background.level2' },
                  }}
                >
                  <Typography level="body-xs" textColor="text.tertiary">
                    {format(parseISO(ev.starts_at), 'EEE, MMM d')}
                    {ev.is_all_day ? ' · All day' : ` · ${format(parseISO(ev.starts_at), 'p')}`}
                  </Typography>
                  <Typography level="body-sm" sx={{ fontWeight: 600 }}>
                    {ev.title}
                  </Typography>
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      </Stack>
    </Card>
  );
}

export default CalendarRail;
