"use client";
/**
 * @file hooks/useCalendars.ts
 * @brief TanStack Query hook for the user's visible calendars.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { listCalendars } from "@/lib/api/calendars";

export function useCalendars() {
  return useQuery({
    queryKey: qk.calendars.list(),
    queryFn: listCalendars,
    staleTime: 60_000,
  });
}
