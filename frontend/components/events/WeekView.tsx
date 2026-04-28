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
import { assignLanes } from "@/lib/events/lanes";

const HOUR_HEIGHT = 48;
const LANE_HEIGHT = 20;

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

  const lanes = React.useMemo(
    () => assignLanes(events, week, subgroupNames),
    [events, week, subgroupNames],
  );

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
          gridTemplateColumns: "repeat(7, 1fr)",
          gap: 0,
          mb: 1,
          px: 0.5,
        }}
      >
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

      {/* Scrollable timeline grid */}
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
        }}
      >
        {/* Hour rows grid */}
        <Box
          sx={{
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
                >
                  {hour === 0 && dayIdx === 0 && (
                    <Typography
                      level="body-xs"
                      sx={{
                        position: "absolute",
                        left: 4,
                        top: 2,
                        fontSize: 10,
                        color: "text.tertiary",
                        pointerEvents: "none",
                      }}
                    >
                      {format(new Date().setHours(hour, 0), "h a")}
                    </Typography>
                  )}
                </Box>
              ))}
            </React.Fragment>
          ))}

          {/* Event blocks overlay */}
          {lanes.map((lane, idx) => {
            const eventStart = parseISO(lane.event.starts_at);
            const startHour = getHours(eventStart);
            const startMin = eventStart.getMinutes();
            const topOffset =
              startHour * HOUR_HEIGHT + (startMin / 60) * HOUR_HEIGHT;

            const eventEnd = parseISO(lane.event.ends_at);
            const endHour = getHours(eventEnd);
            const endMin = eventEnd.getMinutes();
            const endTime = endHour * HOUR_HEIGHT + (endMin / 60) * HOUR_HEIGHT;
            const height = Math.max(LANE_HEIGHT, endTime - topOffset);

            const dayIdx = week.findIndex((d) => {
              const dStart = new Date(d);
              dStart.setHours(0, 0, 0, 0);
              const eStart = new Date(eventStart);
              eStart.setHours(0, 0, 0, 0);
              return dStart.getTime() === eStart.getTime();
            });

            if (dayIdx === -1) return null;

            const isSelected = selectedEventId === lane.event.id;

            return (
              <Box
                key={`event-${lane.event.id}-${idx}`}
                role="button"
                tabIndex={0}
                onClick={() => onSelectEvent(lane.event)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectEvent(lane.event);
                  }
                }}
                sx={{
                  position: "absolute",
                  left: `${(dayIdx * 100) / 7}%`,
                  width: `${(100 / 7) * 0.95}%`,
                  top: topOffset,
                  height,
                  zIndex: 10,
                  px: 0.5,
                  py: 0.25,
                  boxSizing: "border-box",
                  backgroundColor: isSelected
                    ? lane.tone.solid
                    : lane.tone.soft,
                  color: isSelected ? lane.tone.onSolid : lane.tone.onSoft,
                  borderRadius: "4px",
                  fontSize: 11,
                  fontWeight: 600,
                  lineHeight: 1.2,
                  overflow: "hidden",
                  whiteSpace: "nowrap",
                  textOverflow: "ellipsis",
                  cursor: "pointer",
                  border: `1px solid ${isSelected ? lane.tone.solid : "transparent"}`,
                  transition: "all 120ms ease",
                  "&:hover": {
                    backgroundColor: lane.tone.solid,
                    color: lane.tone.onSolid,
                  },
                  "&:focus-visible": {
                    outline: "2px solid",
                    outlineColor: lane.tone.solid,
                    outlineOffset: "1px",
                  },
                }}
              >
                {lane.event.title}
              </Box>
            );
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
