"use client";
/**
 * @file components/events/MonthCalendarLarge.tsx
 * @brief Page-scale monthly calendar. Tall day cells, multi-day spanning event
 *        bars colored per subgroup, day-click selects a date, bar-click
 *        selects an event. Rendered alongside an event rail and detail panel
 *        on /app/events.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
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
} from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { assignLanes, type Lane } from "@/lib/events/lanes";
import { toneForEvent } from "./eventColors";

const LANE_HEIGHT = 22;
const HEADER_OFFSET = 34;
const CELL_MIN_HEIGHT = 104;
const OVERFLOW_RESERVE = 18;
// Lanes that can stack within a day cell without overflowing it vertically.
// Bars rendered beyond this are hidden; per-day "+N more" badge stands in.
const MAX_LANES_VISIBLE = Math.max(
  1,
  Math.floor(
    (CELL_MIN_HEIGHT - HEADER_OFFSET - OVERFLOW_RESERVE) / LANE_HEIGHT,
  ),
);

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
    <Box sx={{ width: "100%" }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(7, 1fr)",
          mb: 1,
          px: 0.5,
        }}
      >
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <Typography
            key={d}
            level="body-xs"
            textColor="text.tertiary"
            sx={{
              textAlign: "left",
              textTransform: "uppercase",
              letterSpacing: "0.14em",
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
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "sm",
          overflow: "hidden",
          backgroundColor: "background.surface",
        }}
      >
        {weeks.map((week, wi) => {
          const segs = weekSegments[wi];
          // Per-day overflow count: how many segs cover this day at a hidden lane.
          const overflowByDay = week.map(
            (_d, di) =>
              segs.filter(
                (s) =>
                  s.lane >= MAX_LANES_VISIBLE &&
                  di >= s.col &&
                  di < s.col + s.span,
              ).length,
          );

          return (
            <Box
              key={wi}
              sx={{
                position: "relative",
                display: "grid",
                gridTemplateColumns: "repeat(7, 1fr)",
                minHeight: 104,
                borderTop: wi === 0 ? "none" : "1px solid",
                borderColor: "divider",
              }}
            >
              {week.map((day, di) => {
                const inMonth = isSameMonth(day, month);
                const today = isToday(day);
                const selected = selectedDay && isSameDay(day, selectedDay);
                const dayOverflow = overflowByDay[di];
                return (
                  <Box
                    key={day.toISOString()}
                    role="button"
                    tabIndex={0}
                    onClick={() => onSelectDay(day)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelectDay(day);
                      }
                    }}
                    sx={{
                      position: "relative",
                      borderLeft: "1px solid",
                      borderColor: "divider",
                      "&:first-of-type": { borderLeft: "none" },
                      px: 1,
                      pt: 0.75,
                      cursor: "pointer",
                      backgroundColor: selected
                        ? "background.level1"
                        : inMonth
                          ? "transparent"
                          : "background.level1",
                      opacity: inMonth ? 1 : 0.55,
                      transition: "background-color 120ms ease",
                      "&:hover": { backgroundColor: "background.level1" },
                      "&:focus-visible": {
                        outline: "2px solid",
                        outlineColor: "primary.solidBg",
                        outlineOffset: "-2px",
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
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          minWidth: 26,
                          height: 26,
                          px: 0.75,
                          borderRadius: "999px",
                          fontSize: 13,
                          fontVariantNumeric: "tabular-nums",
                          fontWeight: today ? 700 : 500,
                          backgroundColor: today
                            ? "primary.solidBg"
                            : "transparent",
                          color: today ? "common.white" : "text.primary",
                        }}
                      >
                        {format(day, "d")}
                      </Box>
                      {wi === 0 || day.getDate() === 1 ? (
                        <Typography
                          level="body-xs"
                          textColor="text.tertiary"
                          sx={{
                            textTransform: "uppercase",
                            letterSpacing: "0.1em",
                            fontWeight: 600,
                          }}
                        >
                          {format(day, "MMM")}
                        </Typography>
                      ) : null}
                    </Stack>
                    {dayOverflow > 0 && (
                      <Box
                        sx={{
                          position: "absolute",
                          left: 4,
                          right: 4,
                          bottom: 2,
                          fontSize: 10,
                          fontWeight: 700,
                          letterSpacing: "0.08em",
                          textTransform: "uppercase",
                          color: "text.tertiary",
                          pointerEvents: "none",
                        }}
                      >
                        +{dayOverflow} more
                      </Box>
                    )}
                  </Box>
                );
              })}

              {/* Event bar overlay */}
              <Box
                sx={{
                  position: "absolute",
                  top: HEADER_OFFSET,
                  left: 0,
                  right: 0,
                  display: "grid",
                  gridTemplateColumns: "repeat(7, 1fr)",
                  pointerEvents: "none",
                }}
              >
                {segs
                  .filter((s) => s.lane < MAX_LANES_VISIBLE)
                  .map((s, i) => {
                    const isSelected = selectedEventId === s.event.id;
                    const solidFill = isSelected || s.event.is_all_day;
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
                          if (e.key === "Enter" || e.key === " ") {
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
                          borderRadius: "4px",
                          borderLeft: s.startsHere
                            ? `3px solid ${s.tone.solid}`
                            : `3px solid ${s.tone.solid}`,
                          backgroundColor: solidFill
                            ? s.tone.solid
                            : s.tone.soft,
                          color: solidFill ? s.tone.onSolid : s.tone.onSoft,
                          fontSize: 12,
                          fontWeight: 600,
                          lineHeight: `${LANE_HEIGHT - 4}px`,
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          pointerEvents: "auto",
                          cursor: "pointer",
                          transition:
                            "background-color 120ms ease, transform 120ms ease",
                          "&:hover": {
                            backgroundColor: s.tone.solid,
                            color: s.tone.onSolid,
                          },
                          "&:focus-visible": {
                            outline: "2px solid",
                            outlineColor: s.tone.solid,
                            outlineOffset: "1px",
                          },
                        }}
                      >
                        {s.startsHere
                          ? `${s.event.is_all_day ? "" : `${format(parseISO(s.event.starts_at), "h:mma").toLowerCase()} · `}${s.event.title}`
                          : " "}
                      </Box>
                    );
                  })}
              </Box>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}

export default MonthCalendarLarge;
