"use client";
/**
 * @file components/home/tiles/FeedTile.tsx
 * @brief Feed tile: home feed in a HomeTile, filtered by the home scope.
 *        A pill filter (?feed=all|kudos|prompts) switches the tile between
 *        the live feed, the embedded Kudos wall and prompt replies.
 */
import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Newspaper } from "lucide-react";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { HomeFeed } from "@/components/home/HomeFeed";
import { KudosWall } from "@/components/feed/KudosWall";
import { Segmented } from "@/components/ui/page";
import { useHomeScope, inScope } from "@/stores/homeScope";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { useHomeSummary } from "@/hooks/useHomeSummary";
import type { FeedItem } from "@/lib/api/home";

type FeedView = "all" | "kudos" | "prompts";

const FEED_OPTIONS: { value: FeedView; label: string }[] = [
  { value: "all", label: "All" },
  { value: "kudos", label: "Kudos" },
  { value: "prompts", label: "Prompts" },
];

/**
 * @brief Feed tile.
 * @param props open state and toggle
 * @return tile element
 */
export function FeedTile({ open, onToggle }: TileSlotProps) {
  const scope = useHomeScope((s) => s.scope);
  const { data: groups } = useSubgroupList();
  const { data: summary } = useHomeSummary();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const raw = params.get("feed");
  const view: FeedView = raw === "kudos" || raw === "prompts" ? raw : "all";

  const setView = (v: FeedView) => {
    const next = new URLSearchParams(params.toString());
    if (v === "all") next.delete("feed");
    else next.set("feed", v);
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };

  const filter = React.useCallback(
    (i: FeedItem) =>
      i.kind === "post"
        ? inScope(i.post.subgroup_id ?? null, scope)
        : scope === "all",
    [scope],
  );
  const promptFilter = React.useCallback(
    (i: FeedItem) =>
      filter(i) &&
      i.kind === "post" &&
      Boolean(i.post.is_prompt_post || i.post.reply_to_prompt_id),
    [filter],
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
      <div className="mb-3">
        <Segmented
          label="Feed filter"
          value={view}
          onChange={setView}
          options={FEED_OPTIONS}
        />
      </div>
      {view === "kudos" ? (
        <div className="md:min-h-0 md:flex-1 md:overflow-y-auto md:overscroll-contain">
          <KudosWall embedded />
        </div>
      ) : view === "prompts" ? (
        <HomeFeed
          embedded
          filter={promptFilter}
          emptyTitle="No prompt replies yet"
        />
      ) : (
        <HomeFeed
          embedded
          filter={filter}
          emptyTitle={
            scope !== "all" && groupName
              ? `Nothing from ${groupName} yet`
              : undefined
          }
        />
      )}
    </HomeTile>
  );
}
