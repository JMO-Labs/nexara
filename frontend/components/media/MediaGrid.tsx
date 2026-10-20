"use client";
/**
 * @file components/media/MediaGrid.tsx
 * @brief Responsive grid of MediaCards.
 */
import * as React from "react";
import { EmptyState, Button } from "@/components/ui";
import { MediaCard } from "./MediaCard";
import type { MediaItem } from "@/lib/api/media";

export interface MediaGridProps {
  items: MediaItem[];
  onSelect?: (m: MediaItem) => void;
}

export function MediaGrid({ items, onSelect }: MediaGridProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="No uploads yet"
        description="Drop files above to upload your first media."
        action={
          <Button variant="secondary" onClick={() => window.scrollTo(0, 0)}>
            Back to upload
          </Button>
        }
      />
    );
  }
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
      {items.map((m) => (
        <MediaCard key={m.id} media={m} onSelect={onSelect} />
      ))}
    </div>
  );
}

export default MediaGrid;
