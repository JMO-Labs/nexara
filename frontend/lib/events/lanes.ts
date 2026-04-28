/**
 * @file lib/events/lanes.ts
 * @brief Shared lane-assignment logic for calendar views.
 *        Computes visual layout: which events overlap, which lane (row) each occupies.
 */
import { isSameDay, parseISO, startOfDay } from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { toneForEvent, type EventTone } from "@/components/events/eventColors";

export interface Lane {
  event: EventItem;
  col: number;
  span: number;
  lane: number;
  startsHere: boolean;
  endsHere: boolean;
  tone: EventTone;
}

/**
 * Check if an event overlaps with a given week.
 */
export function overlaps(
  ev: EventItem,
  weekStart: Date,
  weekEnd: Date,
): boolean {
  const s = startOfDay(parseISO(ev.starts_at));
  const e = startOfDay(parseISO(ev.ends_at));
  return s <= weekEnd && e >= weekStart;
}

/**
 * Assign lanes (rows) to events within a week.
 * Returns a list of segments, each positioned in a grid cell (col + span) and lane.
 */
export function assignLanes(
  events: EventItem[],
  week: Date[],
  subgroupNames: Map<string, string>,
): Lane[] {
  const ws = week[0];
  const we = week[6];
  const lanes: Date[] = [];
  const segs: Lane[] = [];
  const sorted = [...events]
    .filter((e) => overlaps(e, ws, we))
    .sort(
      (a, b) =>
        parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
    );
  for (const ev of sorted) {
    const evStart = startOfDay(parseISO(ev.starts_at));
    const evEnd = startOfDay(parseISO(ev.ends_at));
    const segStart = evStart < ws ? ws : evStart;
    const segEnd = evEnd > we ? we : evEnd;
    const col = Math.round((segStart.getTime() - ws.getTime()) / 86400_000);
    const span =
      Math.round((segEnd.getTime() - segStart.getTime()) / 86400_000) + 1;
    let lane = lanes.findIndex((d) => d < segStart);
    if (lane === -1) {
      lane = lanes.length;
      lanes.push(segEnd);
    } else {
      lanes[lane] = segEnd;
    }
    segs.push({
      event: ev,
      col,
      span,
      lane,
      startsHere: isSameDay(evStart, segStart),
      endsHere: isSameDay(evEnd, segEnd),
      tone: toneForEvent(ev, subgroupNames),
    });
  }
  return segs;
}
