"use client";
/**
 * @file hooks/useTree.ts
 * @brief TanStack Query hooks for the family and group trees.
 */
import { useQuery } from "@tanstack/react-query";
import { getFamilyTree, getGroupTree } from "@/lib/api/tree";
import { useFeature } from "@/hooks/useFeature";

/** @brief Family tree around you, `gens` generations each way. */
export function useFamilyTree(gens: number) {
  const on = useFeature("family_tree");
  return useQuery({
    queryKey: ["tree", "family", gens],
    queryFn: () => getFamilyTree({ gens }),
    enabled: on,
  });
}

/** @brief Relationship tree among the members of a group. */
export function useGroupTree(slug: string) {
  const on = useFeature("family_tree");
  return useQuery({
    queryKey: ["tree", "group", slug],
    queryFn: () => getGroupTree(slug),
    enabled: on,
  });
}
