"use client";
/**
 * @file components/home/tiles/FeedTile.tsx
 * @brief Feed tile: wraps the home feed in a HomeTile (scope filtering later).
 */
import { Newspaper } from "lucide-react";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { HomeFeed } from "@/components/home/HomeFeed";

/**
 * @brief Feed tile.
 * @param props open state and toggle
 * @return tile element
 */
export function FeedTile({ open, onToggle }: TileSlotProps) {
  return (
    <HomeTile
      id="feed"
      title="Feed"
      icon={Newspaper}
      href="/app/feed"
      linkLabel="Open feed"
      open={open}
      onToggle={onToggle}
      className="md:[grid-area:feed] md:overflow-y-auto"
    >
      <HomeFeed />
    </HomeTile>
  );
}
