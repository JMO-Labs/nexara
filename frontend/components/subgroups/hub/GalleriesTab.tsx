"use client";
/**
 * @file components/subgroups/hub/GalleriesTab.tsx
 * @brief Galleries tab: album cards filtered by subgroup.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui";
import { AlbumGrid } from "@/components/photos/AlbumGrid";
import { GalleryCreateModal } from "@/components/galleries/GalleryCreateModal";
import { GalleryUploadModal } from "@/components/galleries/GalleryUploadModal";
import { useGalleryList } from "@/hooks/useGalleries";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface GalleriesTabProps {
  subgroup: SubgroupDetail;
}

export function GalleriesTab({ subgroup }: GalleriesTabProps) {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useGalleryList({
    subgroup_id: subgroup.id,
  });
  const [createOpen, setCreateOpen] = React.useState(false);
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const canEdit = !!subgroup.my_role;

  return (
    <>
      {canEdit && (
        <div className="mb-4 flex flex-wrap justify-end gap-2">
          <Button
            variant="glass"
            className="rounded-full"
            onClick={() => setCreateOpen(true)}
          >
            New album
          </Button>
          <Button variant="primary" onClick={() => setUploadOpen(true)}>
            Upload media
          </Button>
        </div>
      )}
      <AlbumGrid
        items={data?.items}
        isLoading={isLoading}
        error={error}
        onRetry={() => refetch()}
        onSelect={(id) =>
          router.push(`/app/photos?${new URLSearchParams({ gallery: id })}`)
        }
      />
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
