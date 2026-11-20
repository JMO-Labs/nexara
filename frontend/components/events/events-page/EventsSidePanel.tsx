"use client";
/**
 * @file components/events/events-page/EventsSidePanel.tsx
 * @brief Calendar aside: "Up next" panel (upcoming rail) and a selected-day
 *        (or month) list panel. The day panel is hidden in list view.
 */
import { format } from "date-fns";
import { Button } from "@/components/ui";
import { Panel } from "@/components/ui/page";
import { EventRail } from "@/components/events/EventRail";
import type { EventItem } from "@/lib/api/events";

export interface EventsSidePanelProps {
  upcoming: EventItem[];
  railEvents: EventItem[];
  selectedDay: Date | null;
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
  onClearDay: () => void;
  /** Opens the create modal from the empty day state. */
  onCreate?: () => void;
  /** False in list view, where the day panel repeats the list. */
  showDayPanel?: boolean;
}

/**
 * @brief Side panels beside (lg) or below the main calendar.
 * @param props see EventsSidePanelProps
 * @return aside element
 */
export function EventsSidePanel(p: EventsSidePanelProps) {
  const showDayPanel = p.showDayPanel ?? true;
  return (
    <aside
      aria-label="Event list"
      className="flex min-w-0 flex-col gap-4 lg:sticky lg:top-4"
    >
      <Panel title="Up next">
        {p.upcoming.length === 0 ? (
          <p className="text-sm text-muted">Nothing coming up</p>
        ) : (
          <div className="max-h-72 overflow-y-auto">
            <EventRail
              events={p.upcoming}
              selectedDay={null}
              selectedEventId={p.selectedEventId}
              subgroupNames={p.subgroupNames}
              onSelectEvent={p.onSelectEvent}
            />
          </div>
        )}
      </Panel>
      {showDayPanel && (
        <Panel
          title={
            p.selectedDay ? format(p.selectedDay, "EEE, MMM d") : "This month"
          }
          actions={
            p.selectedDay ? (
              <Button variant="glass" size="sm" onClick={p.onClearDay}>
                Clear
              </Button>
            ) : undefined
          }
        >
          <div className="max-h-80 overflow-y-auto">
            <EventRail
              events={p.railEvents}
              selectedDay={p.selectedDay}
              selectedEventId={p.selectedEventId}
              subgroupNames={p.subgroupNames}
              onSelectEvent={p.onSelectEvent}
              emptyAction={
                p.onCreate ? (
                  <Button size="sm" onClick={p.onCreate}>
                    New event
                  </Button>
                ) : undefined
              }
            />
          </div>
        </Panel>
      )}
    </aside>
  );
}
