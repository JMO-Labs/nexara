"use client";
/**
 * @file components/events/WeekView.tsx
 * @brief Weekly calendar grid view. 7 columns, hourly rows (48px each).
 *        Current time line (1px brand) with 6px pulsing dot.
 *        Multi-event overlap allowed via lane assignment.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import {
  format,
  getHours,
  isToday as isTodayFn,
  parseISO,
  addDays,
} from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { assignTimeLanes, type TimeLane } from "@/lib/events/lanes";

const HOUR_HEIGHT = 48;
const LANE_HEIGHT = 20;
const HOUR_LABEL_WIDTH = 50;

export interface WeekViewProps {
  weekStart: Date;
  events: EventItem[];
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
}

export function WeekView({
  weekStart,
  events,
  selectedEventId,
  subgroupNames,
  onSelectEvent,
}: WeekViewProps) {
  // Build 7-day week
  const week = React.useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  );

  /** Per-day lane assignment — events grouped by their start day, then time-overlap lanes within each day. */
  const lanesPerDay = React.useMemo(() => {
    const out: Array<{ day: Date; lanes: TimeLane[] }> = [];
    for (const day of week) {
      const dayStart = new Date(day);
      dayStart.setHours(0, 0, 0, 0);
      const dayEnd = new Date(day);
      dayEnd.setHours(23, 59, 59, 999);
      const dayEvents = events.filter((ev) => {
        const s = parseISO(ev.starts_at);
        const e = parseISO(ev.ends_at);
        return s <= dayEnd && e >= dayStart;
      });
      out.push({
        day,
        lanes: assignTimeLanes(
          dayEvents,
          subgroupNames,
          HOUR_HEIGHT,
          LANE_HEIGHT,
          dayStart,
        ),
      });
    }
    return out;
  }, [events, week, subgroupNames]);

  const now = new Date();
  const currentHour = getHours(now);
  const todayIndex = week.findIndex((d) => isTodayFn(d));

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        fontFamily: "var(--font-body)",
      }}
    >
      {/* Day headers */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: `${HOUR_LABEL_WIDTH}px repeat(7, 1fr)`,
          gap: 0,
          mb: 1,
          px: 0.5,
        }}
      >
        <Box />

        {week.map((day) => {
          const today = isTodayFn(day);
          return (
            <Box
              key={day.toISOString()}
              sx={{
                textAlign: "center",
                py: 0.75,
              }}
            >
              <Typography
                level="body-xs"
                sx={{
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontWeight: 600,
                  color: today ? "primary.solidBg" : "text.secondary",
                  mb: 0.25,
                }}
              >
                {format(day, "EEE")}
              </Typography>
              <Typography
                level="body-sm"
                sx={{
                  fontWeight: today ? 700 : 500,
                  color: today ? "primary.solidBg" : "text.primary",
                }}
              >
                {format(day, "d")}
              </Typography>
            </Box>
          );
        })}
      </Box>

      {/* Scrollable timeline */}
      <Box
        sx={{
          flex: 1,
          overflowY: "auto",
          overflowX: "hidden",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "sm",
          backgroundColor: "background.surface",
          position: "relative",
          display: "flex",
        }}
      >
        {/* Hour label gutter */}
        <Box
          sx={{
            width: HOUR_LABEL_WIDTH,
            flexShrink: 0,
            borderRight: "1px solid",
            borderColor: "divider",
          }}
        >
          {Array.from({ length: 24 }).map((_, hour) => (
            <Box
              key={hour}
              sx={{
                height: HOUR_HEIGHT,
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "flex-end",
                pr: 1,
                pt: 0.25,
                fontSize: 10,
                color: "text.tertiary",
                fontWeight: 600,
                borderBottom: hour < 23 ? "1px solid" : "none",
                borderColor: "divider",
              }}
            >
              {hour === 0 ? "" : format(new Date().setHours(hour, 0), "h a")}
            </Box>
          ))}
        </Box>

        {/* Hour rows grid (7 day columns) */}
        <Box
          sx={{
            flex: 1,
            display: "grid",
            gridTemplateColumns: "repeat(7, 1fr)",
            minHeight: `${24 * HOUR_HEIGHT}px`,
            position: "relative",
          }}
        >
          {Array.from({ length: 24 }).map((_, hour) => (
            <React.Fragment key={hour}>
              {Array.from({ length: 7 }).map((_, dayIdx) => (
                <Box
                  key={`${hour}-${dayIdx}`}
                  sx={{
                    position: "relative",
                    height: HOUR_HEIGHT,
                    borderRight: dayIdx < 6 ? "1px solid" : "none",
                    borderColor: "divider",
                    borderBottom: hour < 23 ? "1px solid" : "none",
                    backgroundColor: "transparent",
                    transition: "background-color 120ms ease",
                    "&:hover": {
                      backgroundColor: "background.level1",
                    },
                  }}
                />
              ))}
            </React.Fragment>
          ))}

          {/* Event blocks overlay — per-day, lane-aware horizontal placement */}
          {lanesPerDay.flatMap(({ lanes }, dayIdx) => {
            const dayWidthPct = 100 / 7;
            const dayLeftPct = dayIdx * dayWidthPct;
            return lanes.map((seg, segIdx) => {
              const isSelected = selectedEventId === seg.event.id;
              const laneWidthPct = dayWidthPct / seg.cluster;
              const leftPct = dayLeftPct + seg.lane * laneWidthPct;
              return (
                <Box
                  key={`event-${seg.event.id}-${dayIdx}-${segIdx}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectEvent(seg.event)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectEvent(seg.event);
                    }
                  }}
                  sx={{
                    position: "absolute",
                    left: `${leftPct}%`,
                    width: `calc(${laneWidthPct}% - 2px)`,
                    top: seg.topOffset,
                    height: seg.height,
                    zIndex: 10,
                    px: 0.5,
                    py: 0.25,
                    boxSizing: "border-box",
                    backgroundColor: isSelected
                      ? seg.tone.solid
                      : seg.tone.soft,
                    color: isSelected ? seg.tone.onSolid : seg.tone.onSoft,
                    borderRadius: "4px",
                    fontSize: 11,
                    fontWeight: 600,
                    lineHeight: 1.2,
                    overflow: "hidden",
                    whiteSpace: "nowrap",
                    textOverflow: "ellipsis",
                    cursor: "pointer",
                    border: `1px solid ${isSelected ? seg.tone.solid : "transparent"}`,
                    transition: "all 120ms ease",
                    "&:hover": {
                      backgroundColor: seg.tone.solid,
                      color: seg.tone.onSolid,
                      zIndex: 11,
                    },
                    "&:focus-visible": {
                      outline: "2px solid",
                      outlineColor: seg.tone.solid,
                      outlineOffset: "1px",
                    },
                  }}
                >
                  {seg.event.title}
                </Box>
              );
            });
          })}

          {/* Current time indicator */}
          {todayIndex !== -1 && (
            <Box
              sx={{
                position: "absolute",
                top: `${currentHour * HOUR_HEIGHT + (now.getMinutes() / 60) * HOUR_HEIGHT}px`,
                left: `${(todayIndex * 100) / 7}%`,
                width: `${100 / 7}%`,
                height: "1px",
                backgroundColor: "primary.solidBg",
                zIndex: 20,
              }}
            >
              <Box
                sx={{
                  position: "absolute",
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  backgroundColor: "primary.solidBg",
                  top: "-2.5px",
                  left: "4px",
                  animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                  "@keyframes pulse": {
                    "0%, 100%": { opacity: 1 },
                    "50%": { opacity: 0.5 },
                  },
                }}
              />
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
}

export default WeekView;
