"use client";
/**
 * @file hooks/useHomePeople.ts
 * @brief Home People query.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getHomePeople } from "@/lib/api/home";

/** @brief Fetch home People (stale after 60s). */
export function useHomePeople() {
  return useQuery({
    queryKey: qk.home.people(),
    queryFn: () => getHomePeople(),
    staleTime: 60_000,
  });
}
