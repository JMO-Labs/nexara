"use client";
/**
 * @file components/subgroups/SubgroupList.tsx
 * @brief Grid of SubgroupCard with skeleton + empty fallbacks.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
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

export function SubgroupList({ onSelect }: SubgroupListProps) {
  const { data, isLoading, error } = useSubgroupList();
  const join = useJoinSubgroup();
  const leave = useLeaveSubgroup();

  if (isLoading) {
    return (
      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
        }}
      >
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} height={120} />
        ))}
      </Box>
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
    <Box
      sx={{
        display: "grid",
        gap: 2,
        gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
      }}
    >
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
    </Box>
  );
}

export default SubgroupList;
