"use client";
/**
 * @file components/subgroups/hub/GalleriesTab.tsx
 * @brief Galleries tab: grid of gallery cards filtered by subgroup.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Button from "@mui/joy/Button";
import { AnimatePresence, motion } from "framer-motion";
import { EmptyState, Skeleton } from "@/components/ui";
import { GalleryCard } from "@/components/galleries/GalleryCard";
import { GalleryCreateModal } from "@/components/galleries/GalleryCreateModal";
import { GalleryUploadModal } from "@/components/galleries/GalleryUploadModal";
import { useGalleryList } from "@/hooks/useGalleries";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface GalleriesTabProps {
  subgroup: SubgroupDetail;
}

export function GalleriesTab({ subgroup }: GalleriesTabProps) {
  const { data, isLoading, error } = useGalleryList({
    subgroup_id: subgroup.id,
  });
  const [createOpen, setCreateOpen] = React.useState(false);
  const [uploadOpen, setUploadOpen] = React.useState(false);

  if (error) {
    return (
      <EmptyState title="Couldn't load galleries" description={String(error)} />
    );
  }

  const galleries = data?.items ?? [];
  const canEdit = !!subgroup.my_role;

  return (
    <>
      {canEdit && (
        <Stack
          direction="row"
          spacing={1}
          justifyContent="flex-end"
          sx={{ mb: 2 }}
        >
          <Button
            variant="outlined"
            color="neutral"
            onClick={() => setCreateOpen(true)}
          >
            New gallery
          </Button>
          <Button variant="soft" onClick={() => setUploadOpen(true)}>
            Upload media
          </Button>
        </Stack>
      )}
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
                  xs: "1fr",
                  md: "repeat(2, 1fr)",
                  lg: "repeat(3, 1fr)",
                },
              }}
            >
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} height={220} />
              ))}
            </Box>
          </motion.div>
        ) : galleries.length === 0 ? (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <EmptyState
              title="No galleries yet"
              description="Be the first to share photos with your community."
            />
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
                  xs: "1fr",
                  md: "repeat(2, 1fr)",
                  lg: "repeat(3, 1fr)",
                },
              }}
            >
              {galleries.map((g) => (
                <motion.div key={g.id} layout>
                  <GalleryCard gallery={g} onSelect={() => {}} />
                </motion.div>
              ))}
            </Box>
          </motion.div>
        )}
      </AnimatePresence>
      <GalleryCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        defaultSubgroupId={subgroup.id}
      />
      <GalleryUploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        subgroupId={subgroup.id}
      />
    </>
  );
}

export default GalleriesTab;
