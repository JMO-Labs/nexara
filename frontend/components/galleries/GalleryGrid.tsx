"use client";
/**
 * @file components/galleries/GalleryGrid.tsx
 * @brief Responsive grid of GalleryCards.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Skeleton, EmptyState, Button } from "@/components/ui";
import { GalleryCard } from "./GalleryCard";
import { useGalleryList } from "@/hooks/useGalleries";
import type { ListGalleriesParams } from "@/lib/api/galleries";

const GRID = "grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4";

export interface GalleryGridProps {
  onSelect: (id: string) => void;
  params?: ListGalleriesParams;
  /** Opens the create-gallery flow from the empty state. */
  onCreate?: () => void;
}

export function GalleryGrid({ onSelect, params, onCreate }: GalleryGridProps) {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useGalleryList(params);

  if (error)
    return (
      <EmptyState
        title="Couldn't load galleries"
        description={error instanceof Error ? error.message : String(error)}
        action={
          <Button variant="secondary" onClick={() => refetch()}>
            Retry
          </Button>
        }
      />
    );
  if (isLoading || !data) {
    return (
      <div className={GRID} aria-busy="true">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height={220} />
        ))}
      </div>
    );
  }
  if (data.items.length === 0) {
    return (
      <EmptyState
        title="No galleries yet"
        description="Create one to share photos."
        action={
          <Button
            variant="primary"
            onClick={() => (onCreate ? onCreate() : router.push("/app/media"))}
          >
            {onCreate ? "Create gallery" : "Browse media"}
          </Button>
        }
      />
    );
  }

  return (
    <div className={GRID}>
      {data.items.map((g) => (
        <GalleryCard key={g.id} gallery={g} onSelect={onSelect} />
      ))}
    </div>
  );
}

export default GalleryGrid;
