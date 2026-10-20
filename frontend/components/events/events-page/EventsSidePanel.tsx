"use client";
/**
 * @file components/events/events-page/EventsSidePanel.tsx
 * @brief Countdown + day-grouped rail shown beside (lg) or below the calendar.
 */
import { EventCountdown } from "@/components/events/EventCountdown";
import { EventRail } from "@/components/events/EventRail";
import type { EventItem } from "@/lib/api/events";

export interface EventsSidePanelProps {
  nextEvent: EventItem | null;
  railEvents: EventItem[];
  selectedDay: Date | null;
  selectedEventId: string | null;
  subgroupNames: Map<string, string>;
  onSelectEvent: (ev: EventItem) => void;
  onClearDay: () => void;
}

/**
 * @brief Side panel with countdown and event rail.
 * @param props see EventsSidePanelProps
 * @return aside element
 */
export function EventsSidePanel(p: EventsSidePanelProps) {
  return (
    <aside
      aria-label="Event list"
      className="bg-surface border-ink/10 flex flex-col overflow-hidden rounded-2xl border lg:sticky lg:top-4 lg:h-[calc(100vh-160px)]"
    >
      {p.nextEvent && (
        <EventCountdown event={p.nextEvent} key={p.nextEvent.id} />
      )}
      <div className="border-ink/10 flex items-center justify-between border-b px-4 py-2">
        <h2 className="text-muted text-sm font-semibold">
          {p.selectedDay ? "This day" : "This month"}
        </h2>
        {p.selectedDay && (
          <button
            type="button"
            onClick={p.onClearDay}
            className="text-muted hover:text-ink min-h-11 px-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Clear
          </button>
        )}
      </div>
      <div className="min-h-0 flex-1">
        <EventRail
          events={p.railEvents}
          selectedDay={p.selectedDay}
          selectedEventId={p.selectedEventId}
          subgroupNames={p.subgroupNames}
          onSelectEvent={p.onSelectEvent}
        />
      </div>
    </aside>
  );
}
