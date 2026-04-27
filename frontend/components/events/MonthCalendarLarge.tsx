'use client';
/**
 * @file components/events/MonthCalendarLarge.tsx
 * @brief Page-scale monthly calendar. Tall day cells, multi-day spanning event
 *        bars colored per subgroup, day-click selects a date, bar-click
 *        selects an event. Rendered alongside an event rail and detail panel
 *        on /app/events.
 */
import * as React from 'react';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import {
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
} from 'date-fns';
import type { EventItem } from '@/lib/api/events';
import { toneForEvent, type EventTone } from './eventColors';

const LANE_HEIGHT = 22;
const HEADER_OFFSET = 34;
const MAX_LANES_VISIBLE = 4;

interface Segment {
  event: EventItem;
  col: number;
  span: number;
  lane: number;
  startsHere: boolean;
  endsHere: boolean;
  tone: EventTone;
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

function overlaps(ev: EventItem, weekStart: Date, weekEnd: Date): boolean {
  const s = startOfDay(parseISO(ev.starts_at));
  const e = startOfDay(parseISO(ev.ends_at));
  return s <= weekEnd && e >= weekStart;
}

function assignLanes(
  events: EventItem[],
  week: Date[],
  subgroupNames: Map<string, string>,
): Segment[] {
  const ws = week[0];
  const we = week[6];
  const lanes: Date[] = [];
  const segs: Segment[] = [];
  const sorted = [...events]
    .filter((e) => overlaps(e, ws, we))
    .sort(
      (a, b) =>
        parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
    );
  for (const ev of sorted) {
    const evStart = startOfDay(parseISO(ev.starts_at));
    const evEnd = startOfDay(parseISO(ev.ends_at));
    const segStart = evStart < ws ? ws : evStart;
    const segEnd = evEnd > we ? we : evEnd;
    const col = Math.round((segStart.getTime() - ws.getTime()) / 86400_000);
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
      tone: toneForEvent(ev, subgroupNames),
    });
  }
  return segs;
}

export interface MonthCalendarLargeProps {
  events: EventItem[];
  month: Date;
  selectedDay: Date | null;
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectDay: (d: Date) => void;
  onSelectEvent: (ev: EventItem) => void;
}

export function MonthCalendarLarge({
  events,
  month,
  selectedDay,
  selectedEventId,
  subgroupNames,
  onSelectDay,
  onSelectEvent,
}: MonthCalendarLargeProps) {
  const weeks = React.useMemo(() => buildWeeks(month), [month]);
  const weekSegments = React.useMemo(
    () => weeks.map((w) => assignLanes(events, w, subgroupNames)),
    [weeks, events, subgroupNames],
  );

  return (
    <Box sx={{ width: '100%' }}>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          mb: 1,
          px: 0.5,
        }}
      >
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
          <Typography
            key={d}
            level="body-xs"
            textColor="text.tertiary"
            sx={{
              textAlign: 'left',
              textTransform: 'uppercase',
              letterSpacing: '0.14em',
              fontWeight: 600,
              py: 0.5,
            }}
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
          backgroundColor: 'background.surface',
        }}
      >
        {weeks.map((week, wi) => {
          const segs = weekSegments[wi];
          const overflow = segs.filter((s) => s.lane >= MAX_LANES_VISIBLE);

          return (
            <Box
              key={wi}
              sx={{
                position: 'relative',
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                minHeight: 104,
                borderTop: wi === 0 ? 'none' : '1px solid',
                borderColor: 'divider',
              }}
            >
              {week.map((day) => {
                const inMonth = isSameMonth(day, month);
                const today = isToday(day);
                const selected = selectedDay && isSameDay(day, selectedDay);
                return (
                  <Box
                    key={day.toISOString()}
                    role="button"
                    tabIndex={0}
                    onClick={() => onSelectDay(day)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelectDay(day);
                      }
                    }}
                    sx={{
                      position: 'relative',
                      borderLeft: '1px solid',
                      borderColor: 'divider',
                      '&:first-of-type': { borderLeft: 'none' },
                      px: 1,
                      pt: 0.75,
                      cursor: 'pointer',
                      backgroundColor: selected
                        ? 'background.level1'
                        : inMonth
                          ? 'transparent'
                          : 'background.level1',
                      opacity: inMonth ? 1 : 0.55,
                      transition: 'background-color 120ms ease',
                      '&:hover': { backgroundColor: 'background.level1' },
                      '&:focus-visible': {
                        outline: '2px solid',
                        outlineColor: 'primary.solidBg',
                        outlineOffset: '-2px',
                      },
                    }}
                  >
                    <Stack
                      direction="row"
                      alignItems="center"
                      justifyContent="space-between"
                    >
                      <Box
                        sx={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          minWidth: 26,
                          height: 26,
                          px: 0.75,
                          borderRadius: '999px',
                          fontSize: 13,
                          fontVariantNumeric: 'tabular-nums',
                          fontWeight: today ? 700 : 500,
                          backgroundColor: today ? 'primary.solidBg' : 'transparent',
                          color: today ? 'common.white' : 'text.primary',
                        }}
                      >
                        {format(day, 'd')}
                      </Box>
                      {wi === 0 || day.getDate() === 1 ? (
                        <Typography
                          level="body-xs"
                          textColor="text.tertiary"
                          sx={{
                            textTransform: 'uppercase',
                            letterSpacing: '0.1em',
                            fontWeight: 600,
                          }}
                        >
                          {format(day, 'MMM')}
                        </Typography>
                      ) : null}
                    </Stack>
                  </Box>
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
                  .map((s, i) => {
                    const isSelected = selectedEventId === s.event.id;
                    return (
                      <Box
                        key={`${s.event.id}-${i}`}
                        role="button"
                        tabIndex={0}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectEvent(s.event);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            onSelectEvent(s.event);
                          }
                        }}
                        title={s.event.title}
                        sx={{
                          gridColumn: `${s.col + 1} / span ${s.span}`,
                          gridRow: 1,
                          transform: `translateY(${s.lane * LANE_HEIGHT}px)`,
                          height: LANE_HEIGHT - 4,
                          mx: 0.4,
                          px: 0.75,
                          borderRadius: '4px',
                          borderLeft: s.startsHere
                            ? `3px solid ${s.tone.solid}`
                            : `3px solid ${s.tone.solid}`,
                          backgroundColor: isSelected ? s.tone.solid : s.tone.soft,
                          color: isSelected ? s.tone.onSolid : s.tone.onSoft,
                          fontSize: 12,
                          fontWeight: 600,
                          lineHeight: `${LANE_HEIGHT - 4}px`,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          pointerEvents: 'auto',
                          cursor: 'pointer',
                          transition:
                            'background-color 120ms ease, transform 120ms ease',
                          '&:hover': {
                            backgroundColor: s.tone.solid,
                            color: s.tone.onSolid,
                          },
                          '&:focus-visible': {
                            outline: '2px solid',
                            outlineColor: s.tone.solid,
                            outlineOffset: '1px',
                          },
                        }}
                      >
                        {s.startsHere
                          ? `${s.event.is_all_day ? '' : `${format(parseISO(s.event.starts_at), 'h:mma').toLowerCase()} · `}${s.event.title}`
                          : ' '}
                      </Box>
                    );
                  })}
                {overflow.length > 0 && (
                  <Box
                    sx={{
                      gridColumn: '1 / span 7',
                      gridRow: 1,
                      transform: `translateY(${MAX_LANES_VISIBLE * LANE_HEIGHT}px)`,
                      px: 1,
                      fontSize: 11,
                      fontWeight: 600,
                      color: 'text.tertiary',
                      textTransform: 'uppercase',
                      letterSpacing: '0.08em',
                      pointerEvents: 'none',
                    }}
                  >
                    + {overflow.length} more
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

export default MonthCalendarLarge;
