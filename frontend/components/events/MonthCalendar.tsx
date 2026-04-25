'use client';
/**
 * @file components/events/MonthCalendar.tsx
 * @brief Month-grid calendar with multi-day spanning event bars and per-day
 *        hover preview popovers. Mirrors Google Calendar layout: week rows,
 *        bars span consecutive days within a week and re-flow to the next
 *        week's row when an event crosses a Sunday boundary.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Tooltip from '@mui/joy/Tooltip';
import {
  addMonths,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  parseISO,
  startOfDay,
  startOfMonth,
  startOfWeek,
  subMonths,
} from 'date-fns';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { IconButton } from '@/components/ui';
import type { EventItem } from '@/lib/api/events';

const LANE_HEIGHT = 18;
const MAX_LANES_VISIBLE = 3;
const HEADER_OFFSET = 26;

interface Segment {
  event: EventItem;
  col: number; // 0-6 within the week
  span: number; // 1-7
  lane: number;
  startsHere: boolean;
  endsHere: boolean;
}

function buildWeeks(month: Date): Date[][] {
  const start = startOfWeek(startOfMonth(month), { weekStartsOn: 0 });
  const end = endOfWeek(endOfMonth(month), { weekStartsOn: 0 });
  const weeks: Date[][] = [];
  let cur = start;
  while (cur <= end) {
    const week: Date[] = [];
    for (let i = 0; i < 7; i++) {
      week.push(cur);
      cur = new Date(cur.getTime() + 86400_000);
    }
    weeks.push(week);
  }
  return weeks;
}

function eventOverlapsWeek(ev: EventItem, weekStart: Date, weekEnd: Date): boolean {
  const s = startOfDay(parseISO(ev.starts_at));
  const e = startOfDay(parseISO(ev.ends_at));
  return s <= weekEnd && e >= weekStart;
}

function assignLanes(events: EventItem[], week: Date[]): Segment[] {
  const weekStart = week[0];
  const weekEnd = week[6];
  const lanes: Date[] = []; // per-lane: last-occupied col-end-date
  const segs: Segment[] = [];
  const sorted = [...events]
    .filter((e) => eventOverlapsWeek(e, weekStart, weekEnd))
    .sort((a, b) => parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime());
  for (const ev of sorted) {
    const evStart = startOfDay(parseISO(ev.starts_at));
    const evEnd = startOfDay(parseISO(ev.ends_at));
    const segStart = evStart < weekStart ? weekStart : evStart;
    const segEnd = evEnd > weekEnd ? weekEnd : evEnd;
    const col = Math.round((segStart.getTime() - weekStart.getTime()) / 86400_000);
    const span =
      Math.round((segEnd.getTime() - segStart.getTime()) / 86400_000) + 1;
    let lane = lanes.findIndex((d) => d < segStart);
    if (lane === -1) {
      lane = lanes.length;
      lanes.push(segEnd);
    } else {
      lanes[lane] = segEnd;
    }
    segs.push({
      event: ev,
      col,
      span,
      lane,
      startsHere: isSameDay(evStart, segStart),
      endsHere: isSameDay(evEnd, segEnd),
    });
  }
  return segs;
}

function eventsOnDay(events: EventItem[], day: Date): EventItem[] {
  return events.filter((ev) => {
    const s = startOfDay(parseISO(ev.starts_at));
    const e = startOfDay(parseISO(ev.ends_at));
    return day >= s && day <= e;
  });
}

function DayPreview({ day, events }: { day: Date; events: EventItem[] }) {
  return (
    <Box sx={{ p: 1, maxWidth: 280, maxHeight: 280, overflowY: 'auto' }}>
      <Typography level="title-sm" sx={{ mb: 0.5 }}>
        {format(day, 'EEEE, MMM d')}
      </Typography>
      {events.length === 0 ? (
        <Typography level="body-xs" textColor="text.tertiary">
          No events
        </Typography>
      ) : (
        <Stack spacing={0.75}>
          {events.map((ev) => (
            <Box key={ev.id}>
              <Typography level="body-xs" textColor="text.tertiary">
                {ev.is_all_day
                  ? 'All day'
                  : format(parseISO(ev.starts_at), 'p')}
                {ev.location ? ` · ${ev.location}` : ''}
              </Typography>
              <Typography level="body-sm" sx={{ fontWeight: 600 }}>
                {ev.title}
              </Typography>
            </Box>
          ))}
        </Stack>
      )}
    </Box>
  );
}

export interface MonthCalendarProps {
  events: EventItem[];
  month: Date;
  onMonthChange: (m: Date) => void;
}

export function MonthCalendar({ events, month, onMonthChange }: MonthCalendarProps) {
  const weeks = React.useMemo(() => buildWeeks(month), [month]);
  const weekSegments = React.useMemo(
    () => weeks.map((w) => assignLanes(events, w)),
    [weeks, events],
  );

  return (
    <Box sx={{ width: '100%' }}>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ mb: 1 }}
      >
        <Typography level="title-md" sx={{ fontFamily: 'var(--font-display)' }}>
          {format(month, 'MMMM yyyy')}
        </Typography>
        <Stack direction="row" spacing={0.5}>
          <IconButton
            size="sm"
            variant="plain"
            aria-label="Previous month"
            onClick={() => onMonthChange(subMonths(month, 1))}
          >
            <ChevronLeftIcon width={16} />
          </IconButton>
          <IconButton
            size="sm"
            variant="plain"
            aria-label="Today"
            onClick={() => onMonthChange(new Date())}
          >
            <Typography level="body-xs">Today</Typography>
          </IconButton>
          <IconButton
            size="sm"
            variant="plain"
            aria-label="Next month"
            onClick={() => onMonthChange(addMonths(month, 1))}
          >
            <ChevronRightIcon width={16} />
          </IconButton>
        </Stack>
      </Stack>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          mb: 0.5,
        }}
      >
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
          <Typography
            key={d}
            level="body-xs"
            textColor="text.tertiary"
            sx={{ textAlign: 'center', textTransform: 'uppercase', letterSpacing: '0.06em' }}
          >
            {d}
          </Typography>
        ))}
      </Box>

      <Stack
        spacing={0}
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 'sm',
          overflow: 'hidden',
        }}
      >
        {weeks.map((week, wi) => {
          const segs = weekSegments[wi];
          const maxLane = segs.reduce((m, s) => Math.max(m, s.lane + 1), 0);
          const visibleLanes = Math.min(maxLane, MAX_LANES_VISIBLE);
          const rowHeight =
            HEADER_OFFSET + visibleLanes * LANE_HEIGHT + (maxLane > MAX_LANES_VISIBLE ? 16 : 4);

          return (
            <Box
              key={wi}
              sx={{
                position: 'relative',
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                minHeight: rowHeight,
                borderTop: wi === 0 ? 'none' : '1px solid',
                borderColor: 'divider',
              }}
            >
              {week.map((day) => {
                const inMonth = isSameMonth(day, month);
                const today = isToday(day);
                const dayEvents = eventsOnDay(events, day);
                return (
                  <Tooltip
                    key={day.toISOString()}
                    title={<DayPreview day={day} events={dayEvents} />}
                    placement="top"
                    variant="outlined"
                    arrow
                    enterDelay={250}
                  >
                    <Box
                      sx={{
                        borderLeft: '1px solid',
                        borderColor: 'divider',
                        '&:first-of-type': { borderLeft: 'none' },
                        p: 0.5,
                        opacity: inMonth ? 1 : 0.45,
                        cursor: 'default',
                        minHeight: rowHeight,
                      }}
                    >
                      <Box
                        sx={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: 22,
                          height: 22,
                          borderRadius: '50%',
                          fontSize: 12,
                          fontWeight: today ? 700 : 500,
                          backgroundColor: today ? 'primary.solidBg' : 'transparent',
                          color: today ? 'common.white' : 'text.primary',
                        }}
                      >
                        {format(day, 'd')}
                      </Box>
                    </Box>
                  </Tooltip>
                );
              })}

              {/* Event bar overlay */}
              <Box
                sx={{
                  position: 'absolute',
                  top: HEADER_OFFSET,
                  left: 0,
                  right: 0,
                  display: 'grid',
                  gridTemplateColumns: 'repeat(7, 1fr)',
                  pointerEvents: 'none',
                }}
              >
                {segs
                  .filter((s) => s.lane < MAX_LANES_VISIBLE)
                  .map((s, i) => (
                    <Box
                      key={`${s.event.id}-${i}`}
                      sx={{
                        gridColumn: `${s.col + 1} / span ${s.span}`,
                        gridRow: 1,
                        transform: `translateY(${s.lane * LANE_HEIGHT}px)`,
                        height: LANE_HEIGHT - 3,
                        mx: 0.25,
                        px: 0.75,
                        borderRadius: s.startsHere && s.endsHere ? 4 : 2,
                        borderTopLeftRadius: s.startsHere ? 4 : 0,
                        borderBottomLeftRadius: s.startsHere ? 4 : 0,
                        borderTopRightRadius: s.endsHere ? 4 : 0,
                        borderBottomRightRadius: s.endsHere ? 4 : 0,
                        backgroundColor: 'primary.solidBg',
                        color: 'common.white',
                        fontSize: 11,
                        lineHeight: `${LANE_HEIGHT - 3}px`,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        pointerEvents: 'auto',
                      }}
                      title={s.event.title}
                    >
                      {s.startsHere ? s.event.title : ' '}
                    </Box>
                  ))}
                {segs.some((s) => s.lane >= MAX_LANES_VISIBLE) && (
                  <Box
                    sx={{
                      gridColumn: '1 / span 7',
                      gridRow: 1,
                      transform: `translateY(${MAX_LANES_VISIBLE * LANE_HEIGHT}px)`,
                      px: 0.5,
                      fontSize: 10,
                      color: 'text.tertiary',
                      pointerEvents: 'none',
                    }}
                  >
                    + more
                  </Box>
                )}
              </Box>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}

export default MonthCalendar;
