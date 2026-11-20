"use client";
/**
 * @file components/events/events-page/EventsSidePanel.tsx
 * @brief Calendar aside: "Up next" panel (upcoming rail) and a selected-day
 *        (or month) list panel.
 */
import { format } from "date-fns";
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
}

/**
 * @brief Side panels beside (lg) or below the main calendar.
 * @param props see EventsSidePanelProps
 * @return aside element
 */
export function EventsSidePanel(p: EventsSidePanelProps) {
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
      <Panel
        title={
          p.selectedDay ? format(p.selectedDay, "EEEE, MMM d") : "This month"
        }
        actions={
          p.selectedDay ? (
            <button
              type="button"
              onClick={p.onClearDay}
              className="min-h-11 px-2 text-sm text-muted outline-none hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Clear
            </button>
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
          />
        </div>
      </Panel>
    </aside>
  );
}
