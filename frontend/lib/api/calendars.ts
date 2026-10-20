/**
 * @file lib/api/calendars.ts
 * @brief Calendars REST endpoint — list calendars visible to current user.
 */
import { apiGet } from "./client";

export type CalendarKind = "personal" | "community" | "subgroup";

export interface Calendar {
  id: string;
  kind: CalendarKind;
  name: string;
  color: string | null;
  owner_id: string | null;
  subgroup_id: string | null;
  external_provider: string | null;
  external_id: string | null;
  created_at: string;
}

const BASE = "/api/v1/calendars";

export const listCalendars = () => apiGet<Calendar[]>(BASE);
