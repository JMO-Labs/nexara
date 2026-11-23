/**
 * @file lib/api/trips.ts
 * @brief Safe-arrival REST client. Trips carry no location, only a label and
 *        an expected arrival time (UTC ISO strings).
 */
import { apiDelete, apiGet, apiPost, seg } from "./client";

export interface TripPerson {
  id: string;
  display_name: string;
}

export interface Trip {
  id: string;
  label: string;
  expected_at: string;
  arrived_at: string | null;
  alerted_at: string | null;
  ended_at: string | null;
  traveler: TripPerson;
  /** Only filled for the traveler. */
  watchers: TripPerson[];
}

export interface TripCreate {
  label: string;
  expected_at: string;
  watcher_ids: string[];
}

const BASE = "/api/v1/trips";

export const startTrip = (body: TripCreate) => apiPost<Trip>(BASE, body);
export const getActiveTrip = () => apiGet<Trip | null>(`${BASE}/active`);
export const listWatching = () => apiGet<Trip[]>(`${BASE}/watching`);
export const arriveTrip = (id: string) =>
  apiPost<Trip>(`${BASE}/${seg(id)}/arrive`);
export const extendTrip = (id: string, expected_at: string) =>
  apiPost<Trip>(`${BASE}/${seg(id)}/extend`, { expected_at });
export const cancelTrip = (id: string) => apiDelete(`${BASE}/${seg(id)}`);
