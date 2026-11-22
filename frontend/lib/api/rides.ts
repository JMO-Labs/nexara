/**
 * @file lib/api/rides.ts
 * @brief Event ride REST client (offers, requests, join/leave, answer, cancel).
 */
import { apiDelete, apiGet, apiPost, seg } from "./client";

export interface RidePassenger {
  user_id: string;
  display_name: string;
  seats: number;
}

export interface Ride {
  id: string;
  event_id: string;
  kind: "offer" | "request";
  user_id: string;
  driver_name: string;
  seats: number;
  seats_left: number;
  origin: string;
  depart_at: string | null;
  note: string;
  passengers: RidePassenger[];
  joined: boolean;
  created_at: string;
}

export interface RideCreate {
  seats: number;
  origin: string;
  depart_at: string | null;
  note: string;
}

const ev = (id: string) => `/api/v1/events/${seg(id)}/rides`;
const rd = (id: string) => `/api/v1/rides/${seg(id)}`;

export const listRides = (eventId: string) => apiGet<Ride[]>(ev(eventId));
export const offerRide = (eventId: string, body: RideCreate) =>
  apiPost<Ride>(`${ev(eventId)}/offers`, body);
export const requestRide = (eventId: string, body: RideCreate) =>
  apiPost<Ride>(`${ev(eventId)}/requests`, body);
export const joinRide = (rideId: string, seats = 1) =>
  apiPost<Ride>(`${rd(rideId)}/join`, { seats });
export const leaveRide = (rideId: string) =>
  apiPost<void>(`${rd(rideId)}/leave`);
export const answerRequest = (requestId: string, offerId: string) =>
  apiPost<Ride>(`${rd(requestId)}/answer`, { offer_id: offerId });
export const cancelRide = (rideId: string) => apiDelete(rd(rideId));
