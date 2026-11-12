"use client";
/**
 * @file components/galleries/GalleryGrid.tsx
 * @brief Responsive grid of GalleryCards.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Skeleton, EmptyState, Button } from "@/components/ui";
import { fadeInOut, useMotionProps } from "@/components/ui/motion";
import { GalleryCard } from "./GalleryCard";
import { useGalleryList } from "@/hooks/useGalleries";
import type { ListGalleriesParams } from "@/lib/api/galleries";

const GRID = "grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4";

export interface GalleryGridProps {
  onSelect: (id: string) => void;
  params?: ListGalleriesParams;
}

export function GalleryGrid({ onSelect, params }: GalleryGridProps) {
  const router = useRouter();
  const { data, isLoading, error } = useGalleryList(params);
  const fade = useMotionProps(fadeInOut);

  if (error)
    return (
      <EmptyState
        title="Couldn't load galleries"
        description={String(error)}
        action={
          <Button variant="secondary" onClick={() => router.refresh()}>
            Retry
          </Button>
        }
      />
    );
  if (isLoading || !data) {
    return (
      <motion.div className={GRID} data-testid="gallery-skeleton" {...fade}>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height={220} />
        ))}
      </motion.div>
    );
  }
  if (data.items.length === 0) {
    return (
      <EmptyState
        title="No galleries yet"
        description="Create one to share photos."
        action={
          <Button variant="primary" onClick={() => router.push("/app/media")}>
            Browse media
          </Button>
        }
      />
    );
  }

  return (
    <div className={GRID}>
      <AnimatePresence mode="popLayout">
        {data.items.map((g) => (
          <motion.div
            key={g.id}
            data-testid="gallery-item"
            {...fade}
            {...(Object.keys(fade).length ? { layout: true } : {})}
          >
            <GalleryCard gallery={g} onSelect={onSelect} />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

export default GalleryGrid;
