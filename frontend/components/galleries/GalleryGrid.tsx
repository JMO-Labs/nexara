"use client";
/**
 * @file components/galleries/GalleryGrid.tsx
 * @brief Responsive grid of GalleryCards.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import Box from "@mui/joy/Box";
import { AnimatePresence, motion } from "framer-motion";
import { Skeleton, EmptyState, Button } from "@/components/ui";
import { GalleryCard } from "./GalleryCard";
import { useGalleryList } from "@/hooks/useGalleries";
import type { ListGalleriesParams } from "@/lib/api/galleries";

export interface GalleryGridProps {
  onSelect: (id: string) => void;
  params?: ListGalleriesParams;
}

export function GalleryGrid({ onSelect, params }: GalleryGridProps) {
  const router = useRouter();
  const { data, isLoading, error } = useGalleryList(params);

  if (error)
    return (
      <EmptyState
        title="Couldn't load galleries"
        description={String(error)}
        action={
          <Button variant="soft" onClick={() => router.refresh()}>
            Retry
          </Button>
        }
      />
    );
  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No galleries yet"
        description="Create one to share photos."
        action={
          <Button variant="solid" onClick={() => router.push("/app/media")}>
            Browse media
          </Button>
        }
      />
    );
  }

  return (
    <AnimatePresence mode="wait">
      {isLoading ? (
        <motion.div
          key="sk"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
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
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} height={220} />
            ))}
          </Box>
        </motion.div>
      ) : (
        <motion.div
          key="ct"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
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
            {data.items.map((g) => (
              <motion.div key={g.id} layout>
                <GalleryCard gallery={g} onSelect={onSelect} />
              </motion.div>
            ))}
          </Box>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default GalleryGrid;
