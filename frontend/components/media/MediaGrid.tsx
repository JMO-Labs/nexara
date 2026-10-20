"use client";
/**
 * @file components/media/MediaGrid.tsx
 * @brief Responsive grid of MediaCards.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
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
          <Button variant="soft" onClick={() => window.scrollTo(0, 0)}>
            Back to upload
          </Button>
        }
      />
    );
  }
  return (
    <Box
      sx={{
        display: "grid",
        gap: 2,
        gridTemplateColumns: {
          xs: "1fr 1fr",
          md: "repeat(3, 1fr)",
          lg: "repeat(4, 1fr)",
        },
      }}
    >
      {items.map((m) => (
        <MediaCard key={m.id} media={m} onSelect={onSelect} />
      ))}
    </Box>
  );
}

export default MediaGrid;
