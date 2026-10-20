/**
 * @file lib/events/lanes.ts
 * @brief Shared lane-assignment logic for calendar views.
 *        Computes visual layout: which events overlap, which lane (row) each occupies.
 */
import { isSameDay, parseISO, startOfDay } from "date-fns";
import type { EventItem } from "@/lib/api/events";
import { toneForEvent, type EventTone } from "@/components/events/eventColors";

export interface TimeLane {
  event: EventItem;
  lane: number;
  /** Total concurrent lanes in this event's overlap cluster (>=1). Use to compute width. */
  cluster: number;
  topOffset: number;
  height: number;
  tone: EventTone;
}

/**
 * Time-based lane assignment for hourly views (Day / Week column).
 * Sweep-line: events that overlap in time share a cluster; cluster.cluster is
 * the max concurrent lane count so width = 1/cluster.
 *
 * @param events Already filtered to a single day's events (any order).
 * @param subgroupNames Lookup for tone resolution.
 * @param hourHeight Pixel height of one hour row.
 * @param minHeight Minimum block height in px (short events).
 */
export function assignTimeLanes(
  events: EventItem[],
  subgroupNames: Map<string, string>,
  hourHeight: number,
  minHeight: number,
  dayStart?: Date,
): TimeLane[] {
  if (events.length === 0) return [];
  const sorted = [...events].sort(
    (a, b) => parseISO(a.starts_at).getTime() - parseISO(b.starts_at).getTime(),
  );

  type Item = {
    ev: EventItem;
    s: number;
    e: number;
    topOffset: number;
    height: number;
  };
  const dayBaseMs = dayStart ? startOfDay(dayStart).getTime() : null;

  const items: Item[] = sorted.map((ev) => {
    const evStart = parseISO(ev.starts_at);
    const evEnd = parseISO(ev.ends_at);
    let startMin: number;
    let endMin: number;
    if (dayBaseMs !== null) {
      const dayEndMs = dayBaseMs + 24 * 60 * 60_000;
      const sMs = Math.max(evStart.getTime(), dayBaseMs);
      const eMs = Math.min(evEnd.getTime(), dayEndMs);
      startMin = (sMs - dayBaseMs) / 60_000;
      endMin = (eMs - dayBaseMs) / 60_000;
    } else {
      startMin = evStart.getHours() * 60 + evStart.getMinutes();
      endMin = evEnd.getHours() * 60 + evEnd.getMinutes();
    }
    const topOffset = (startMin / 60) * hourHeight;
    const height = Math.max(minHeight, ((endMin - startMin) / 60) * hourHeight);
    return { ev, s: startMin, e: endMin, topOffset, height };
  });

  // Greedy lane fill — assign each item to lowest-numbered lane whose last
  // event ends at or before this item's start.
  const laneEnds: number[] = [];
  const laneOf = new Map<EventItem, number>();
  for (const it of items) {
    let lane = laneEnds.findIndex((end) => end <= it.s);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(it.e);
    } else {
      laneEnds[lane] = it.e;
    }
    laneOf.set(it.ev, lane);
  }

  // Cluster sizing — for each item, find max lanes among overlapping items
  // (transitive: if A overlaps B and B overlaps C, all share cluster size).
  // Build undirected overlap graph, BFS to find connected components.
  const idx = new Map(items.map((it, i) => [it.ev, i] as const));
  const adj: number[][] = items.map(() => []);
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      if (items[i].s < items[j].e && items[j].s < items[i].e) {
        adj[i].push(j);
        adj[j].push(i);
      }
    }
  }
  const compOf = new Array(items.length).fill(-1);
  const compMaxLanes: number[] = [];
  for (let i = 0; i < items.length; i++) {
    if (compOf[i] !== -1) continue;
    const compId = compMaxLanes.length;
    let maxLane = 0;
    const stack = [i];
    while (stack.length) {
      const k = stack.pop()!;
      if (compOf[k] !== -1) continue;
      compOf[k] = compId;
      maxLane = Math.max(maxLane, laneOf.get(items[k].ev)!);
      for (const n of adj[k]) if (compOf[n] === -1) stack.push(n);
    }
    compMaxLanes.push(maxLane + 1);
  }

  return items.map((it) => ({
    event: it.ev,
    lane: laneOf.get(it.ev)!,
    cluster: compMaxLanes[compOf[idx.get(it.ev)!]],
    topOffset: it.topOffset,
    height: it.height,
    tone: toneForEvent(it.ev, subgroupNames),
  }));
}

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
