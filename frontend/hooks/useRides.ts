"use client";
/**
 * @file hooks/useRides.ts
 * @brief TanStack Query hooks for event rides; every mutation refetches the list.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  answerRequest,
  cancelRide,
  joinRide,
  leaveRide,
  listRides,
  offerRide,
  requestRide,
  type RideCreate,
} from "@/lib/api/rides";

const key = (eventId: string) => ["event-rides", eventId] as const;

/** @brief Rides for an event (disabled when the feature is off). */
export const useRides = (eventId: string, enabled: boolean) =>
  useQuery({
    queryKey: key(eventId),
    queryFn: () => listRides(eventId),
    enabled,
  });

/** @brief All ride mutations for one event. */
export function useRideActions(eventId: string) {
  const qc = useQueryClient();
  const onSettled = () => qc.invalidateQueries({ queryKey: key(eventId) });
  const useMk = <V>(fn: (v: V) => Promise<unknown>) =>
    useMutation({ mutationFn: fn, onSettled });
  return {
    offer: useMk((b: RideCreate) => offerRide(eventId, b)),
    request: useMk((b: RideCreate) => requestRide(eventId, b)),
    join: useMk((id: string) => joinRide(id)),
    leave: useMk((id: string) => leaveRide(id)),
    cancel: useMk((id: string) => cancelRide(id)),
    answer: useMk((v: { requestId: string; offerId: string }) =>
      answerRequest(v.requestId, v.offerId),
    ),
  };
}
