'use client';
/**
 * @file components/events/EventRail.tsx
 * @brief Right-side rail for /app/events. Renders the visible month's events
 *        sorted ascending and grouped by day, with a colored dot per
 *        subgroup. Selecting a row syncs with the calendar + detail panel.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { format, isSameDay, parseISO, startOfDay } from 'date-fns';
import { EmptyState } from '@/components/ui';
import type { EventItem } from '@/lib/api/events';
import { toneForEvent } from './eventColors';

export interface EventRailProps {
  events: EventItem[];
  selectedDay: Date | null;
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
}

function dayKey(iso: string): string {
  return format(parseISO(iso), 'yyyy-MM-dd');
}

export function EventRail({
  events,
  selectedDay,
  selectedEventId,
  subgroupNames,
  onSelectEvent,
}: EventRailProps) {
  const sorted = React.useMemo(
    () =>
      [...events].sort(
        (a, b) =>
          parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
      ),
    [events],
  );

  const groups = React.useMemo(() => {
    const map = new Map<string, EventItem[]>();
    for (const ev of sorted) {
      const k = dayKey(ev.starts_at);
      const arr = map.get(k) ?? [];
      arr.push(ev);
      map.set(k, arr);
    }
    return Array.from(map.entries());
  }, [sorted]);

  // Auto-scroll selected day group into view
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  React.useEffect(() => {
    if (!selectedDay || !containerRef.current) return;
    const k = format(selectedDay, 'yyyy-MM-dd');
    const el = containerRef.current.querySelector<HTMLElement>(
      `[data-day="${k}"]`,
    );
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [selectedDay]);

  if (groups.length === 0) {
    return (
      <Box sx={{ p: 2 }}>
        <EmptyState
          compact
          title="Nothing this month"
          description="Switch months or clear filters to see more events."
        />
      </Box>
    );
  }

  return (
    <Box
      ref={containerRef}
      sx={{
        height: '100%',
        overflowY: 'auto',
        px: 1.5,
        py: 1,
        scrollbarGutter: 'stable',
      }}
    >
      {groups.map(([key, items]) => {
        const day = parseISO(items[0].starts_at);
        const isSelectedDay =
          selectedDay && isSameDay(startOfDay(day), startOfDay(selectedDay));
        return (
          <Box
            key={key}
            data-day={key}
            sx={{ mb: 2, scrollMarginTop: 8 }}
          >
            <Stack
              direction="row"
              alignItems="baseline"
              spacing={1}
              sx={{
                position: 'sticky',
                top: 0,
                py: 0.5,
                bgcolor: 'background.body',
                zIndex: 1,
                borderBottom: '1px solid',
                borderColor: 'divider',
                mb: 1,
              }}
            >
              <Typography
                level="title-md"
                sx={{
                  fontFamily: 'var(--font-display)',
                  fontVariantNumeric: 'tabular-nums',
                  color: isSelectedDay ? 'primary.plainColor' : 'text.primary',
                }}
              >
                {format(day, 'd')}
              </Typography>
              <Typography
                level="body-xs"
                textColor="text.tertiary"
                sx={{
                  textTransform: 'uppercase',
                  letterSpacing: '0.14em',
                  fontWeight: 600,
                }}
              >
                {format(day, 'EEE · MMM')}
              </Typography>
            </Stack>

            <Stack spacing={0.5}>
              {items.map((ev) => {
                const tone = toneForEvent(ev, subgroupNames);
                const selected = selectedEventId === ev.id;
                return (
                  <Box
                    key={ev.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => onSelectEvent(ev)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelectEvent(ev);
                      }
                    }}
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: '8px 1fr',
                      gap: 1,
                      alignItems: 'stretch',
                      px: 1,
                      py: 1,
                      borderRadius: 'sm',
                      cursor: 'pointer',
                      backgroundColor: selected
                        ? tone.soft
                        : 'transparent',
                      transition: 'background-color 120ms ease',
                      '&:hover': { backgroundColor: tone.soft },
                      '&:focus-visible': {
                        outline: '2px solid',
                        outlineColor: tone.solid,
                        outlineOffset: '2px',
                      },
                    }}
                  >
                    <Box
                      sx={{
                        width: 4,
                        borderRadius: '2px',
                        backgroundColor: tone.solid,
                      }}
                    />
                    <Box sx={{ minWidth: 0 }}>
                      <Typography
                        level="body-xs"
                        textColor="text.tertiary"
                        sx={{
                          fontVariantNumeric: 'tabular-nums',
                          letterSpacing: '0.04em',
                        }}
                      >
                        {ev.is_all_day
                          ? 'All day'
                          : `${format(parseISO(ev.starts_at), 'h:mm a')} – ${format(parseISO(ev.ends_at), 'h:mm a')}`}
                        {ev.location ? ` · ${ev.location}` : ''}
                      </Typography>
                      <Typography
                        level="body-sm"
                        sx={{
                          fontWeight: 600,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                        }}
                      >
                        {ev.title}
                      </Typography>
                      <Typography
                        level="body-xs"
                        sx={{
                          mt: 0.25,
                          color: tone.onSoft,
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          letterSpacing: '0.1em',
                          fontSize: 10,
                        }}
                      >
                        {tone.label}
                      </Typography>
                    </Box>
                  </Box>
                );
              })}
            </Stack>
          </Box>
        );
      })}
    </Box>
  );
}

export default EventRail;
