"use client";
/**
 * @file components/home/widgets/UpcomingEventsWidget.tsx
 * @brief Editorial upcoming-events list. Events grouped by day with
 *        uppercase tracking-wide date headers (matches the events page
 *        ListView). Compact rows: time · title · source. Click opens
 *        EventDetailPanel.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Box from "@mui/joy/Box";
import { useUpcomingEvents } from "@/hooks/useEvents";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { EmptyState, Skeleton } from "@/components/ui";
import { EventDetailPanel } from "@/components/events/EventDetailPanel";
import { SourceBadge } from "@/components/feed/SourceBadge";
import type { EventItem } from "@/lib/api/events";
import type { Subgroup } from "@/lib/api/subgroups";
import type { WidgetContext } from "@/lib/widgets/registry";
import { useWidgetDrag } from "@/stores/widgetDrag";
import { format, parseISO, isToday, isTomorrow, isSameDay } from "date-fns";

const DAYS_OPTIONS = [7, 14, 30] as const;

function formatDayHeader(d: Date): string {
  if (isToday(d)) return "Today";
  if (isTomorrow(d)) return "Tomorrow";
  return format(d, "EEE · MMM d").toUpperCase();
}

function formatTime(d: Date, allDay: boolean): string {
  if (allDay) return "All day";
  return format(d, "h:mm a").toLowerCase();
}

export function UpcomingEventsWidget({ instanceId }: WidgetContext) {
  const [days, setDays] = React.useState<7 | 14 | 30>(14);
  const [filterSubgroupId, setFilterSubgroupId] = React.useState<
    string | undefined
  >(undefined);
  const [selectedEvent, setSelectedEvent] = React.useState<EventItem | null>(
    null,
  );
  const disableDrag = useWidgetDrag((s) => s.disable);
  const enableDrag = useWidgetDrag((s) => s.enable);

  React.useEffect(() => {
    if (selectedEvent) disableDrag(instanceId);
    else enableDrag(instanceId);
    return () => enableDrag(instanceId);
  }, [selectedEvent, instanceId, disableDrag, enableDrag]);

  const { data, isLoading } = useUpcomingEvents(days, filterSubgroupId);
  const { data: subgroupsData } = useSubgroupList();
  const events = data?.items ?? [];

  const subgroupNameMap = React.useMemo(() => {
    const m = new Map<string, string>();
    ((subgroupsData as Subgroup[] | undefined) ?? []).forEach((sg) =>
      m.set(sg.id, sg.name),
    );
    return m;
  }, [subgroupsData]);

  const subgroups = (subgroupsData as Subgroup[] | undefined) ?? [];

  // Group events by day.
  const grouped = React.useMemo(() => {
    const out: Array<{ day: Date; items: EventItem[] }> = [];
    for (const e of events) {
      const d = parseISO(e.starts_at);
      const last = out[out.length - 1];
      if (last && isSameDay(last.day, d)) {
        last.items.push(e);
      } else {
        out.push({ day: d, items: [e] });
      }
    }
    return out;
  }, [events]);

  const PillButton = ({
    active,
    onClick,
    label,
  }: {
    active: boolean;
    onClick: () => void;
    label: string;
  }) => (
    <Box
      component="button"
      type="button"
      aria-pressed={active}
      onClick={onClick}
      sx={{
        px: 1.25,
        py: 0.4,
        borderRadius: "sm",
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: "0.02em",
        border: "1px solid",
        borderColor: active ? "primary.500" : "divider",
        bgcolor: active ? "primary.softBg" : "transparent",
        color: active ? "primary.plainColor" : "text.secondary",
        cursor: "pointer",
        transition: "all 120ms",
        "&:hover": { borderColor: active ? "primary.500" : "neutral.300" },
      }}
    >
      {label}
    </Box>
  );

  return (
    <Box sx={{ position: "relative" }}>
      {/* Controls */}
      <Stack
        direction="row"
        spacing={0.75}
        sx={{ flexWrap: "wrap", alignItems: "center", mb: 1.5 }}
      >
        <Stack direction="row" spacing={0.5}>
          {DAYS_OPTIONS.map((d) => (
            <PillButton
              key={d}
              active={days === d}
              onClick={() => setDays(d)}
              label={`${d}d`}
            />
          ))}
        </Stack>
        {subgroups.length > 0 && (
          <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap" }}>
            <PillButton
              active={filterSubgroupId === undefined}
              onClick={() => setFilterSubgroupId(undefined)}
              label="All"
            />
            {subgroups.slice(0, 4).map((sg) => (
              <PillButton
                key={sg.id}
                active={filterSubgroupId === sg.id}
                onClick={() => setFilterSubgroupId(sg.id)}
                label={sg.name}
              />
            ))}
          </Stack>
        )}
      </Stack>

      {/* List */}
      {isLoading ? (
        <Stack spacing={1}>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={48} rounded="md" />
          ))}
        </Stack>
      ) : grouped.length === 0 ? (
        <EmptyState
          title="No upcoming events"
          description={`Nothing scheduled in the next ${days} days.`}
        />
      ) : (
        <Stack spacing={2}>
          {grouped.map(({ day, items }) => (
            <Box key={day.toISOString()}>
              <Typography
                level="body-xs"
                sx={{
                  textTransform: "uppercase",
                  letterSpacing: "0.14em",
                  color: "text.tertiary",
                  fontWeight: 600,
                  mb: 0.75,
                }}
              >
                {formatDayHeader(day)}
              </Typography>
              <Stack
                spacing={0}
                sx={{
                  borderTop: "1px solid",
                  borderColor: "divider",
                }}
              >
                {items.map((event) => {
                  const start = parseISO(event.starts_at);
                  return (
                    <Box
                      key={event.id}
                      component="button"
                      type="button"
                      onClick={() => setSelectedEvent(event)}
                      sx={{
                        all: "unset",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "baseline",
                        gap: 1.5,
                        px: 0,
                        py: 1,
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        transition: "background-color 120ms",
                        "&:hover": { bgcolor: "background.level1" },
                        "&:focus-visible": {
                          outline: "2px solid var(--nx-palette-focusVisible)",
                          outlineOffset: 2,
                        },
                      }}
                    >
                      <Typography
                        level="body-xs"
                        sx={{
                          fontVariantNumeric: "tabular-nums",
                          color: "text.tertiary",
                          width: 64,
                          flexShrink: 0,
                          pl: 1,
                        }}
                      >
                        {formatTime(start, event.is_all_day)}
                      </Typography>
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography
                          level="body-sm"
                          sx={{
                            color: "text.primary",
                            fontWeight: 500,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {event.title}
                        </Typography>
                      </Box>
                      <Box sx={{ flexShrink: 0, pr: 1 }}>
                        <SourceBadge
                          subgroupId={event.subgroup_id}
                          subgroupName={
                            event.subgroup_id
                              ? (subgroupNameMap.get(event.subgroup_id) ?? null)
                              : null
                          }
                          subgroupSlug={event.subgroup_slug ?? null}
                        />
                      </Box>
                    </Box>
                  );
                })}
              </Stack>
            </Box>
          ))}
        </Stack>
      )}

      <EventDetailPanel
        event={selectedEvent}
        subgroupNames={subgroupNameMap}
        onClose={() => setSelectedEvent(null)}
      />
    </Box>
  );
}

export default UpcomingEventsWidget;
