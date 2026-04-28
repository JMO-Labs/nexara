"use client";
/**
 * @file components/events/DayView.tsx
 * @brief Single-day calendar view. Hour ticks on left, events in single column.
 *        Multi-event overlap allowed with left-edge positioning.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import { format, getHours, parseISO } from "date-fns";
import type { EventItem } from "@/lib/api/events";
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
  // Filter events for this day
  const dayEvents = React.useMemo(() => {
    const dayStart = new Date(day);
    dayStart.setHours(0, 0, 0, 0);
    const dayEnd = new Date(day);
    dayEnd.setHours(23, 59, 59, 999);

    return events.filter((ev) => {
      const evStart = parseISO(ev.starts_at);
      const evEnd = parseISO(ev.ends_at);
      return evStart <= dayEnd && evEnd >= dayStart;
    });
  }, [day, events]);

  // Assign lanes to events
  const lanes = React.useMemo(() => {
    const lanes: Date[] = [];
    const segs: Array<{
      event: EventItem;
      lane: number;
      topOffset: number;
      height: number;
      tone: ReturnType<typeof toneForEvent>;
    }> = [];

    const sorted = [...dayEvents].sort(
      (a, b) =>
        parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
    );

    for (const ev of sorted) {
      const evStart = parseISO(ev.starts_at);
      const evEnd = parseISO(ev.ends_at);

      const startHour = getHours(evStart);
      const startMin = evStart.getMinutes();
      const topOffset = startHour * HOUR_HEIGHT + (startMin / 60) * HOUR_HEIGHT;

      const endHour = getHours(evEnd);
      const endMin = evEnd.getMinutes();
      const endTime = endHour * HOUR_HEIGHT + (endMin / 60) * HOUR_HEIGHT;
      const height = Math.max(LANE_HEIGHT, endTime - topOffset);

      let lane = lanes.findIndex((d) => d < evStart);
      if (lane === -1) {
        lane = lanes.length;
        lanes.push(evEnd);
      } else {
        lanes[lane] = evEnd;
      }

      segs.push({
        event: ev,
        lane,
        topOffset,
        height,
        tone: toneForEvent(ev, subgroupNames),
      });
    }

    return segs;
  }, [dayEvents, subgroupNames]);

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

          {/* Event blocks */}
          {lanes.map((seg, idx) => {
            const isSelected = selectedEventId === seg.event.id;
            const maxLanes = Math.max(
              1,
              lanes.filter((s) => s.lane <= seg.lane).length,
            );
            const laneWidth = Math.max(20, 100 / maxLanes);
            const leftOffset = seg.lane * laneWidth;

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
                  left: `${leftOffset}%`,
                  width: `${laneWidth * 0.95}%`,
                  height: seg.height,
                  px: 0.5,
                  py: 0.25,
                  boxSizing: "border-box",
                  backgroundColor: isSelected ? seg.tone.solid : seg.tone.soft,
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
                  },
                  "&:focus-visible": {
                    outline: "2px solid",
                    outlineColor: seg.tone.solid,
                    outlineOffset: "1px",
                  },
                  zIndex: 10,
                }}
              >
                {seg.event.title}
              </Box>
            );
          })}
        </Box>
      </Box>
    </Box>
  );
}

export default DayView;
