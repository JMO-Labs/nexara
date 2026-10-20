"use client";
/**
 * @file components/events/DayView.tsx
 * @brief Single-day calendar view. Hour ticks on left, events in single column.
 *        Multi-event overlap allowed with left-edge positioning.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import { format, isToday as isTodayFn, parseISO } from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { assignTimeLanes } from "@/lib/events/lanes";
import { toneForEvent } from "./eventColors";

const HOUR_HEIGHT = 48;
const LANE_HEIGHT = 20;
const HOUR_LABEL_WIDTH = 50;

export interface DayViewProps {
  day: Date;
  events: EventItem[];
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
}

export function DayView({
  day,
  events,
  selectedEventId,
  subgroupNames,
  onSelectEvent,
}: DayViewProps) {
  // Split events into all-day and timed for this day
  const { allDay, timed } = React.useMemo(() => {
    const dayStart = new Date(day);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(day);
    dayEnd.setHours(23, 59, 59, 999);

    const allDay: EventItem[] = [];
    const timed: EventItem[] = [];
    for (const ev of events) {
      const evStart = parseISO(ev.starts_at);
      const evEnd = parseISO(ev.ends_at);
      if (!(evStart <= dayEnd && evEnd >= dayStart)) continue;
      // Treat as all-day if flagged or if it spans the entire visible day.
      const spansFullDay =
        evStart.getTime() <= dayStart.getTime() &&
        evEnd.getTime() >= dayEnd.getTime();
      if (ev.is_all_day || spansFullDay) allDay.push(ev);
      else timed.push(ev);
    }
    return { allDay, timed };
  }, [day, events]);

  const lanes = React.useMemo(
    () => assignTimeLanes(timed, subgroupNames, HOUR_HEIGHT, LANE_HEIGHT, day),
    [timed, subgroupNames, day],
  );

  // Current-time indicator (only when day === today)
  const [now, setNow] = React.useState(() => new Date());
  React.useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);
  const isToday = isTodayFn(day);
  const nowOffset = (now.getHours() + now.getMinutes() / 60) * HOUR_HEIGHT;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
      }}
    >
      {/* Day header */}
      <Box
        sx={{
          textAlign: "center",
          py: 1.5,
          borderBottom: "1px solid",
          borderColor: "divider",
          mb: 1,
        }}
      >
        <Typography level="h3" sx={{ mb: 0.25 }}>
          {format(day, "EEEE")}
        </Typography>
        <Typography level="body-sm" sx={{ color: "text.secondary" }}>
          {format(day, "MMMM d, yyyy")}
        </Typography>
      </Box>

      {/* All-day strip */}
      {allDay.length > 0 && (
        <Box
          sx={{
            display: "flex",
            alignItems: "stretch",
            gap: 0.5,
            mb: 1,
            pl: `${HOUR_LABEL_WIDTH}px`,
            pr: 0.5,
          }}
        >
          <Box
            sx={{
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              color: "text.tertiary",
              alignSelf: "center",
              position: "absolute",
              left: 4,
              width: HOUR_LABEL_WIDTH - 8,
              textAlign: "right",
            }}
          >
            All day
          </Box>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, flex: 1 }}>
            {allDay.map((ev) => {
              const tone = toneForEvent(ev, subgroupNames);
              const isSelected = selectedEventId === ev.id;
              return (
                <Box
                  key={ev.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => onSelectEvent(ev)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelectEvent(ev);
                    }
                  }}
                  sx={{
                    px: 1,
                    py: 0.5,
                    borderRadius: "4px",
                    fontSize: 11,
                    fontWeight: 600,
                    backgroundColor: isSelected ? tone.solid : tone.soft,
                    color: isSelected ? tone.onSolid : tone.onSoft,
                    cursor: "pointer",
                    border: `1px solid ${isSelected ? tone.solid : "transparent"}`,
                    "&:hover": {
                      backgroundColor: tone.solid,
                      color: tone.onSolid,
                    },
                  }}
                >
                  {ev.title}
                </Box>
              );
            })}
          </Box>
        </Box>
      )}

      {/* Timeline grid */}
      <Box
        sx={{
          flex: 1,
          overflowY: "auto",
          overflowX: "hidden",
          position: "relative",
          display: "flex",
          minHeight: 0,
        }}
      >
        {/* Hour labels and lines */}
        <Box
          sx={{
            width: HOUR_LABEL_WIDTH,
            flexShrink: 0,
            borderRight: "1px solid",
            borderColor: "divider",
            pt: 0.5,
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
                borderBottom: hour < 23 ? "1px solid" : "none",
                borderColor: "divider",
                fontSize: 11,
                color: "text.tertiary",
                fontWeight: 600,
              }}
            >
              {format(new Date().setHours(hour, 0), "h a")}
            </Box>
          ))}
        </Box>

        {/* Events container */}
        <Box
          sx={{
            flex: 1,
            position: "relative",
            minHeight: `${24 * HOUR_HEIGHT}px`,
          }}
        >
          {/* Grid background */}
          {Array.from({ length: 24 }).map((_, hour) => (
            <Box
              key={hour}
              sx={{
                position: "absolute",
                top: hour * HOUR_HEIGHT,
                left: 0,
                right: 0,
                height: HOUR_HEIGHT,
                borderBottom: hour < 23 ? "1px solid" : "none",
                borderColor: "divider",
              }}
            />
          ))}

          {/* Current-time indicator */}
          {isToday && (
            <Box
              sx={{
                position: "absolute",
                top: nowOffset,
                left: 0,
                right: 0,
                height: 0,
                zIndex: 20,
                pointerEvents: "none",
                borderTop: "2px solid",
                borderColor: "danger.solidBg",
              }}
            >
              <Box
                sx={{
                  position: "absolute",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: "danger.solidBg",
                  top: "-5px",
                  left: -4,
                  boxShadow: "0 0 0 2px var(--joy-palette-background-surface)",
                  animation:
                    "pulse-now 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                  "@keyframes pulse-now": {
                    "0%, 100%": { opacity: 1 },
                    "50%": { opacity: 0.55 },
                  },
                }}
              />
            </Box>
          )}

          {/* Event blocks */}
          {lanes.map((seg, idx) => {
            const isSelected = selectedEventId === seg.event.id;
            const laneWidthPct = 100 / seg.cluster;
            const leftPct = seg.lane * laneWidthPct;

            return (
              <Box
                key={`event-${seg.event.id}-${idx}`}
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
                  top: seg.topOffset,
                  left: `${leftPct}%`,
                  width: `calc(${laneWidthPct}% - 4px)`,
                  height: seg.height,
                  px: 0.75,
                  py: 0.5,
                  boxSizing: "border-box",
                  backgroundColor: isSelected ? seg.tone.solid : seg.tone.soft,
                  color: isSelected ? seg.tone.onSolid : seg.tone.onSoft,
                  borderRadius: "4px",
                  fontSize: 11,
                  fontWeight: 600,
                  lineHeight: 1.2,
                  overflow: "hidden",
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
                  zIndex: 10,
                }}
              >
                <Typography
                  level="body-xs"
                  sx={{
                    color: "inherit",
                    fontWeight: 700,
                    fontSize: 11,
                    lineHeight: 1.15,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {seg.event.title}
                </Typography>
                {seg.height >= 32 && (
                  <Typography
                    level="body-xs"
                    sx={{
                      color: "inherit",
                      opacity: 0.8,
                      fontSize: 10,
                      mt: "1px",
                    }}
                  >
                    {format(parseISO(seg.event.starts_at), "h:mm a")}
                  </Typography>
                )}
              </Box>
            );
          })}
        </Box>
      </Box>
    </Box>
  );
}

export default DayView;
