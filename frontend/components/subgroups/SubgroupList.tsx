"use client";
/**
 * @file components/subgroups/SubgroupList.tsx
 * @brief Grid of SubgroupCard with skeleton + empty fallbacks.
 */
import * as React from "react";
import { Skeleton, EmptyState } from "@/components/ui";
import { SubgroupCard } from "./SubgroupCard";
import {
  useSubgroupList,
  useJoinSubgroup,
  useLeaveSubgroup,
} from "@/hooks/useSubgroups";

export interface SubgroupListProps {
  onSelect: (slug: string) => void;
}

const GRID = "grid grid-cols-1 gap-4 md:grid-cols-2";

/**
 * @brief Subgroup grid.
 * @param props onSelect callback
 * @return grid, skeletons or empty state
 */
export function SubgroupList({ onSelect }: SubgroupListProps) {
  const { data, isLoading, error } = useSubgroupList();
  const join = useJoinSubgroup();
  const leave = useLeaveSubgroup();

  if (isLoading) {
    return (
      <div className={GRID}>
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} height={120} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState title="Couldn't load subgroups" description={String(error)} />
    );
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="No subgroups yet"
        description="Create one to organize conversations and events around a smaller circle."
      />
    );
  }

  return (
    <div className={GRID}>
      {data.map((sg) => (
        <SubgroupCard
          key={sg.id}
          subgroup={sg}
          onSelect={onSelect}
          onJoin={(slug) => join.mutate(slug)}
          onLeave={(slug) => leave.mutate(slug)}
          busy={
            (join.isPending && join.variables === sg.slug) ||
            (leave.isPending && leave.variables === sg.slug)
          }
        />
      ))}
    </div>
  );
}

export default SubgroupList;
