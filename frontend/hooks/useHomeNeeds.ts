"use client";
/**
 * @file hooks/useHomeNeeds.ts
 * @brief Home Needs query.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getHomeNeeds } from "@/lib/api/home";

/** @brief Fetch home Needs (stale after 60s). */
export function useHomeNeeds() {
  return useQuery({
    queryKey: qk.home.needs(),
    queryFn: () => getHomeNeeds(),
    staleTime: 60_000,
  });
}
