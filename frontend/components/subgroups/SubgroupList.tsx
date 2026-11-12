"use client";
/**
 * @file components/subgroups/SubgroupList.tsx
 * @brief Grid of SubgroupCard with skeleton + empty fallbacks.
 */
import * as React from "react";
import { Button, Skeleton, EmptyState } from "@/components/ui";
import { SubgroupCard } from "./SubgroupCard";
import {
  useSubgroupList,
  useJoinSubgroup,
  useLeaveSubgroup,
} from "@/hooks/useSubgroups";

export interface SubgroupListProps {
  onSelect: (slug: string) => void;
  /** Shown as the empty-state CTA when provided. */
  onCreate?: () => void;
}

const GRID = "grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3";

/**
 * @brief Subgroup grid.
 * @param props onSelect and optional onCreate callbacks
 * @return grid, skeletons or empty state
 */
export function SubgroupList({ onSelect, onCreate }: SubgroupListProps) {
  const { data, isLoading, error, refetch } = useSubgroupList();
  const join = useJoinSubgroup();
  const leave = useLeaveSubgroup();

  if (isLoading) {
    return (
      <div
        className={GRID}
        role="status"
        aria-busy="true"
        aria-label="Loading groups"
      >
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} height={220} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        title="Couldn't load subgroups"
        description={error instanceof Error ? error.message : String(error)}
        action={<Button onClick={() => refetch()}>Retry</Button>}
      />
    );
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="No groups yet"
        description="Create one to organize conversations and events around a smaller circle."
        action={onCreate && <Button onClick={onCreate}>Create group</Button>}
      />
    );
  }

  return (
    <ul className={GRID}>
      {data.map((sg, i) => (
        <li
          key={sg.id}
          style={{ animationDelay: `${Math.min(i, 8) * 40}ms` }}
          className="motion-safe:animate-in motion-safe:fade-in motion-safe:fill-mode-both"
        >
          <SubgroupCard
            subgroup={sg}
            onSelect={onSelect}
            onJoin={(slug) => join.mutate(slug)}
            onLeave={(slug) => leave.mutate(slug)}
            busy={
              (join.isPending && join.variables === sg.slug) ||
              (leave.isPending && leave.variables === sg.slug)
            }
          />
        </li>
      ))}
    </ul>
  );
}

export default SubgroupList;
