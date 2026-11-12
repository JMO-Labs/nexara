"use client";
/**
 * @file components/subgroups/hub/GalleriesTab.tsx
 * @brief Galleries tab: grid of gallery cards filtered by subgroup.
 */
import * as React from "react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
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

  const grid = "grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3";

  return (
    <>
      {canEdit && (
        <div className="mb-4 flex flex-wrap justify-end gap-2">
          <Button variant="outline" onClick={() => setCreateOpen(true)}>
            New gallery
          </Button>
          <Button variant="primary" onClick={() => setUploadOpen(true)}>
            Upload media
          </Button>
        </div>
      )}
      {isLoading ? (
        <div className={grid}>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={220} />
          ))}
        </div>
      ) : galleries.length === 0 ? (
        <EmptyState
          title="No galleries yet"
          description="Be the first to share photos with your community."
        />
      ) : (
        <div className={grid}>
          {galleries.map((g) => (
            <div key={g.id}>
              <GalleryCard gallery={g} onSelect={() => {}} />
            </div>
          ))}
        </div>
      )}
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
