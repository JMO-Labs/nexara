"use client";
/**
 * @file hooks/useTrips.ts
 * @brief Safe-arrival queries (own active trip, trips I watch) and the shared
 *        invalidation key. Both poll once a minute so overdue state stays fresh.
 */
import { useQuery } from "@tanstack/react-query";
import { getActiveTrip, listWatching } from "@/lib/api/trips";
import { useFeature } from "@/hooks/useFeature";

export const TRIPS_KEY = ["trips"] as const;

/** @return the viewer's active trip (undefined while loading / flag off) */
export function useActiveTrip() {
  const on = useFeature("safe_arrival");
  return useQuery({
    queryKey: [...TRIPS_KEY, "active"],
    queryFn: getActiveTrip,
    enabled: on,
    refetchInterval: 60_000,
  });
}

/** @return active trips of people the viewer watches */
export function useWatchingTrips() {
  const on = useFeature("safe_arrival");
  return useQuery({
    queryKey: [...TRIPS_KEY, "watching"],
    queryFn: listWatching,
    enabled: on,
    refetchInterval: 60_000,
  });
}
