/**
 * @file lib/celebrations.ts
 * @brief Celebrations shown on the calendar as all-day entries of a
 *        synthetic "Birthdays" calendar (ids start with "cel:").
 */
import type { Calendar } from "@/lib/api/calendars";
import type { CalendarCelebration } from "@/lib/api/celebrations";
import type { EventItem } from "@/lib/api/events";

export const CELEBRATIONS_CALENDAR_ID = "celebrations";
const PREFIX = "cel:";

/** @brief Synthetic calendar so the filter bar can toggle celebrations. */
export const CELEBRATIONS_CALENDAR: Calendar = {
  id: CELEBRATIONS_CALENDAR_ID,
  kind: "personal",
  name: "Birthdays",
  color: "#c9973f",
  owner_id: null,
  subgroup_id: null,
  external_provider: null,
  external_id: null,
  created_at: "1970-01-01T00:00:00Z",
};

export type CelebrationEvent = EventItem & {
  celebration: CalendarCelebration;
};

/** @brief Title as shown on the calendar. */
export const celebrationTitle = (c: CalendarCelebration) =>
  c.occasion === "gotcha_day"
    ? `${c.name}'s gotcha day`
    : `${c.name}'s birthday`;

/** @brief Map celebrations to all-day calendar entries (local dates). */
export function celebrationEvents(
  list: CalendarCelebration[],
): CelebrationEvent[] {
  return list.map((c) => ({
    id: `${PREFIX}${c.subject_type}:${c.subject_id}:${c.occasion}:${c.date}`,
    author_id: "",
    title: celebrationTitle(c),
    description: null,
    location: null,
    starts_at: `${c.date}T00:00:00`,
    ends_at: `${c.date}T23:59:59`,
    is_all_day: true,
    recurrence_rule: null,
    visibility: "community",
    subgroup_id: null,
    subgroup_slug: null,
    calendar_id: CELEBRATIONS_CALENDAR_ID,
    color: CELEBRATIONS_CALENDAR.color,
    latitude: null,
    longitude: null,
    rsvp_labels: null,
    rsvp_counts: {},
    contribution_slots: [],
    user_rsvp: null,
    created_at: "",
    updated_at: "",
    celebration: c,
  }));
}

/** @brief The celebration behind a calendar entry, if it is one. */
export function celebrationOf(ev: EventItem): CalendarCelebration | null {
  return ev.id.startsWith(PREFIX)
    ? ((ev as CelebrationEvent).celebration ?? null)
    : null;
}
