"use client";
/**
 * @file components/subgroups/hub/TreeTab.tsx
 * @brief Group hub Tree tab: how the group's members are related.
 */
import { EmptyState, Skeleton } from "@/components/ui";
import { FamilyTree } from "@/components/tree/FamilyTree";
import { useGroupTree } from "@/hooks/useTree";
import type { SubgroupDetail } from "@/lib/api/subgroups";

/**
 * @param subgroup the group
 * @return tab body
 */
export function TreeTab({ subgroup }: { subgroup: SubgroupDetail }) {
  const { data, isLoading } = useGroupTree(subgroup.slug);
  if (isLoading) return <Skeleton className="h-72 w-full" />;
  if (!data || data.nodes.length === 0)
    return (
      <EmptyState
        title="Nothing to show yet"
        description="Members' relations appear here."
      />
    );
  return <FamilyTree data={data} defaultShowFriends />;
}
