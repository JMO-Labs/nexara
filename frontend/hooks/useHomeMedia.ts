/**
 * @file hooks/useHomeMedia.ts
 * @brief TanStack Query hook for aggregated home media carousel data.
 */
"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getHomeMedia, type HomeMediaResponse } from "@/lib/api/home";

export type HomeMediaScope = "all" | "community" | "subgroup" | "personal";

export interface UseHomeMediaParams {
  limit?: number;
  scope?: HomeMediaScope;
  subgroupId?: string;
}

/**
 * @brief Fetch aggregated media items visible to the current user.
 *
 * Stale time: 5 minutes. Query key includes scope/subgroup so cache splits
 * cleanly across filters.
 */
export function useHomeMedia(
  arg?: number | UseHomeMediaParams,
): UseQueryResult<HomeMediaResponse> {
  const params: UseHomeMediaParams =
    typeof arg === "number" ? { limit: arg } : (arg ?? {});
  const limit = params.limit ?? 24;
  const scope: HomeMediaScope = params.scope ?? "all";
  const subgroupId = params.subgroupId;
  return useQuery({
    queryKey: [...qk.home.media(limit), scope, subgroupId ?? null],
    queryFn: () => getHomeMedia({ limit, scope, subgroupId }),
    staleTime: 5 * 60_000,
  });
}
