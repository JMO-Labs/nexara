"use client";
/**
 * @file components/home/tiles/FeedTile.tsx
 * @brief Feed tile: home feed in a HomeTile, filtered by the home scope.
 */
import * as React from "react";
import { Newspaper } from "lucide-react";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { HomeFeed } from "@/components/home/HomeFeed";
import { useHomeScope, inScope } from "@/stores/homeScope";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useHomeSummary } from "@/hooks/useHomeSummary";
import type { FeedItem } from "@/lib/api/home";

/**
 * @brief Feed tile.
 * @param props open state and toggle
 * @return tile element
 */
export function FeedTile({ open, onToggle }: TileSlotProps) {
  const scope = useHomeScope((s) => s.scope);
  const { data: groups } = useSubgroupList();
  const { data: summary } = useHomeSummary();
  const filter = React.useCallback(
    (i: FeedItem) =>
      i.kind === "post"
        ? inScope(i.post.subgroup_id ?? null, scope)
        : scope === "all",
    [scope],
  );
  const groupName = groups?.find((g) => g.id === scope)?.name;
  const n = summary?.new_posts ?? 0;
  return (
    <HomeTile
      id="feed"
      title="Feed"
      icon={Newspaper}
      href="/app#feed"
      linkLabel="Open feed"
      summary={n > 0 ? `${n} new posts` : undefined}
      count={n}
      open={open}
      onToggle={onToggle}
      className="md:[grid-area:feed]"
    >
      <HomeFeed
        embedded
        filter={filter}
        emptyTitle={
          scope !== "all" && groupName
            ? `Nothing from ${groupName} yet`
            : undefined
        }
      />
    </HomeTile>
  );
}
