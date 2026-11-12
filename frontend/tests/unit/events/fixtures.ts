/**
 * @file tests/unit/events/fixtures.ts
 * @brief Shared EventItem factory for event component tests.
 */
import type { EventItem } from "@/lib/api/events";

export function makeEvent(over: Partial<EventItem> = {}): EventItem {
  return {
    id: "e1",
    author_id: "u1",
    title: "Picnic",
    description: null,
    location: null,
    starts_at: "2026-05-10T10:00:00",
    ends_at: "2026-05-10T11:00:00",
    is_all_day: false,
    recurrence_rule: null,
    visibility: "community",
    subgroup_id: null,
    subgroup_slug: null,
    calendar_id: null,
    color: null,
    latitude: null,
    longitude: null,
    rsvp_labels: {},
    rsvp_counts: {},
    contribution_slots: [],
    user_rsvp: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    ...over,
  };
}
