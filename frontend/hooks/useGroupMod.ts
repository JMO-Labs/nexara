"use client";
/**
 * @file hooks/useGroupMod.ts
 * @brief Whether the viewer owns or moderates a given group.
 */
import { useSubgroupList } from "@/hooks/useSubgroups";

/**
 * @param subgroupId group id (null/undefined for community scope)
 * @return true when my_role is owner or moderator there
 */
export function useIsGroupMod(subgroupId?: string | null): boolean {
  const { data } = useSubgroupList();
  if (!subgroupId) return false;
  const g = (data ?? []).find((s) => s.id === subgroupId);
  return g?.my_role === "owner" || g?.my_role === "moderator";
}
