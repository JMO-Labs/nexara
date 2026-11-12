/**
 * @file lib/api/events.ts
 * @brief Events REST endpoints (list window) + RSVP, contributions, CRUD.
 */
import { apiGet, apiPost, apiPatch, apiPut, apiDelete, seg } from "./client";

export interface EventItem {
  id: string;
  author_id: string;
  title: string;
  description: string | null;
  location: string | null;
  starts_at: string;
  ends_at: string;
  is_all_day: boolean;
  recurrence_rule: string | null;
  visibility: string;
  subgroup_id: string | null;
  subgroup_slug: string | null;
  calendar_id: string | null;
  color: string | null;
  latitude: number | null;
  longitude: number | null;
  rsvp_labels: Record<string, string> | null;
  rsvp_counts: Record<string, number>;
  contribution_slots: ContributionSlot[];
  user_rsvp: { status: string } | null;
  gallery_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContributionSlot {
  id: string | null;
  title: string;
  quantity_needed: number;
  quantity_claimed: number;
  claimed_by: string[];
}

export interface EventListResponse {
  items: EventItem[];
  next_cursor: string | null;
  has_more: boolean;
}

export interface CreateEventBody {
  title: string;
  description?: string | null;
  location?: string | null;
  starts_at: string;
  ends_at: string;
  is_all_day?: boolean;
  visibility?: "community" | "subgroup" | "private";
  subgroup_id?: string | null;
  color?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  rsvp_labels?: Record<string, string> | null;
  contribution_slots?: ContributionSlot[];
  auto_create_gallery?: boolean;
}

const BASE = "/api/v1/events";

export interface ListEventsParams {
  start?: string;
  end?: string;
  limit?: number;
  subgroup_id?: string;
}

export const listEvents = (params: ListEventsParams = {}) => {
  const qs = new URLSearchParams();
  if (params.start) qs.set("start", params.start);
  if (params.end) qs.set("end", params.end);
  qs.set("limit", String(params.limit ?? 100));
  if (params.subgroup_id) qs.set("subgroup_id", params.subgroup_id);
  return apiGet<EventListResponse>(`${BASE}?${qs}`);
};

export const getEvent = (id: string) => apiGet<EventItem>(`${BASE}/${seg(id)}`);
export const createEvent = (body: CreateEventBody) =>
  apiPost<EventItem>(BASE, body);
export const updateEvent = (id: string, body: Partial<CreateEventBody>) =>
  apiPatch<EventItem>(`${BASE}/${seg(id)}`, body);
export const deleteEvent = (id: string) =>
  apiDelete<{ message: string }>(`${BASE}/${seg(id)}`);
export const rsvpEvent = (id: string, status: string, note?: string) =>
  apiPost<{ id: string; event_id: string; user_id: string; status: string }>(
    `${BASE}/${seg(id)}/rsvp`,
    { status, note },
  );
export const unrsvpEvent = (id: string) =>
  apiDelete<{ message: string }>(`${BASE}/${seg(id)}/rsvp`);
export const claimContribution = (
  eventId: string,
  slotId: string,
  quantity = 1,
) =>
  apiPost<EventItem>(
    `${BASE}/${seg(eventId)}/contributions/${seg(slotId)}/claim`,
    {
      quantity,
    },
  );
export const unclaimContribution = (eventId: string, slotId: string) =>
  apiDelete<EventItem>(
    `${BASE}/${seg(eventId)}/contributions/${seg(slotId)}/claim`,
  );

export interface CalendarSubscription {
  id: string;
  title: string;
  source_url: string;
  last_synced_at: string | null;
  sync_error: string | null;
  sync_interval_minutes: number;
  sync_enabled?: boolean;
}

export interface CreateSubscriptionBody {
  title: string;
  source_url: string;
  sync_interval_minutes?: number;
}

export type UpdateSubscriptionBody = Partial<
  Pick<
    CalendarSubscription,
    "title" | "source_url" | "sync_interval_minutes" | "sync_enabled"
  >
>;

const SUBS_BASE = "/api/v1/calendar-subscriptions";

/** Backend names the display field `name`; the UI calls it `title`. */
type Wire = Omit<CalendarSubscription, "title"> & { name: string };
const fromWire = ({ name, ...rest }: Wire): CalendarSubscription => ({
  ...rest,
  title: name,
});
const toWire = ({ title, ...rest }: Partial<CalendarSubscription>) => ({
  ...(title !== undefined ? { name: title } : {}),
  ...rest,
});

export const listSubscriptions = async () =>
  (await apiGet<Wire[]>(SUBS_BASE)).map(fromWire);
export const createSubscription = async (body: CreateSubscriptionBody) =>
  fromWire(await apiPost<Wire>(SUBS_BASE, toWire(body)));
export const updateSubscription = async (
  id: string,
  body: UpdateSubscriptionBody,
) => fromWire(await apiPut<Wire>(`${SUBS_BASE}/${seg(id)}`, toWire(body)));
export const deleteSubscription = (id: string) =>
  apiDelete<{ message: string }>(`${SUBS_BASE}/${seg(id)}`);
export const syncNowSubscription = (id: string) =>
  apiPost<{ synced_count: number }>(`${SUBS_BASE}/${seg(id)}/sync`, {});
