"use client";
/**
 * @file components/home/widgets/FeedWidget.tsx
 * @brief Home widget that renders the unified community + subgroup feed.
 *        Reuses FeedView which already handles infinite scroll and PostCard
 *        (PostCard now renders SourceBadge for attribution).
 */
import * as React from "react";
import { FeedView } from "@/components/feed/FeedView";
import type { WidgetContext } from "@/lib/widgets/registry";

export function FeedWidget(_: WidgetContext) {
  return <FeedView />;
}

export default FeedWidget;
