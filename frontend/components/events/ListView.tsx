"use client";
/**
 * @file components/events/ListView.tsx
 * @brief List view grouped by date. Date headers in uppercase, event rows with color bar.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import { format, parseISO, startOfDay, isSameDay } from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { toneForEvent } from "./eventColors";

export interface ListViewProps {
  events: EventItem[];
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
}

export function ListView({
  events,
  selectedEventId,
  subgroupNames,
  onSelectEvent,
}: ListViewProps) {
  // Group events by date
  const grouped = React.useMemo(() => {
    const groups = new Map<string, EventItem[]>();
    for (const ev of events) {
      const day = startOfDay(parseISO(ev.starts_at));
      const key = day.toISOString();
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key)!.push(ev);
    }

    // Sort by date and within each day by start time
    const sorted: [string, EventItem[]][] = [];
    for (const [date, items] of groups) {
      items.sort(
        (a, b) =>
          parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
      );
      sorted.push([date, items]);
    }
    sorted.sort((a, b) => a[0].localeCompare(b[0]));
    return sorted;
  }, [events]);

  if (grouped.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <Typography level="body-sm" sx={{ color: "text.tertiary" }}>
          No events scheduled
        </Typography>
      </Box>
    );
  }

  return (
    <Stack
      spacing={0}
      sx={{
        width: "100%",
        maxHeight: "100%",
        overflowY: "auto",
        px: 0,
      }}
    >
      {grouped.map(([dateKey, dayEvents]) => {
        const date = new Date(dateKey);
        const isToday = isSameDay(date, new Date());

        return (
          <Box key={dateKey} sx={{ mb: 2 }}>
            {/* Date header */}
            <Typography
              level="body-xs"
              sx={{
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                fontWeight: 700,
                color: isToday ? "primary.solidBg" : "text.secondary",
                mb: 0.75,
                px: 1.5,
              }}
            >
              {format(date, "EEEE, MMMM d")}
            </Typography>

            {/* Event list for this day */}
            <Stack spacing={0.5} sx={{ px: 0 }}>
              {dayEvents.map((ev) => {
                const isSelected = selectedEventId === ev.id;
                const tone = toneForEvent(ev, subgroupNames);
                const startTime = format(parseISO(ev.starts_at), "h:mm a");
                const endTime = format(parseISO(ev.ends_at), "h:mm a");

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
                      display: "flex",
                      alignItems: "center",
                      px: 1.5,
                      py: 1,
                      backgroundColor: isSelected
                        ? "background.level1"
                        : "transparent",
                      borderLeft: `4px solid ${tone.solid}`,
                      borderRadius: 0,
                      cursor: "pointer",
                      transition: "background-color 120ms ease",
                      "&:hover": {
                        backgroundColor: "background.level1",
                      },
                      "&:focus-visible": {
                        outline: "2px solid",
                        outlineColor: tone.solid,
                        outlineOffset: "-2px",
                      },
                    }}
                  >
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography
                        level="body-sm"
                        sx={{
                          fontWeight: 600,
                          color: "text.primary",
                          mb: 0.25,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {ev.title}
                      </Typography>
                      <Typography
                        level="body-xs"
                        sx={{
                          color: "text.secondary",
                        }}
                      >
                        {ev.is_all_day
                          ? "All day"
                          : `${startTime} – ${endTime}`}
                      </Typography>
                    </Box>
                  </Box>
                );
              })}
            </Stack>
          </Box>
        );
      })}
    </Stack>
  );
}

export default ListView;
