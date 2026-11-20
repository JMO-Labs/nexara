"use client";
/**
 * @file components/members/MemberGalleriesTab.tsx
 * @brief Member profile albums tab displaying the owner's albums.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { AlbumGrid } from "@/components/photos/AlbumGrid";
import { useGalleryList } from "@/hooks/useGalleries";

export interface MemberGalleriesTabProps {
  userId: string;
}

/**
 * @brief Album cards for galleries owned by a member.
 * @param userId owner id filter
 * @return album grid
 */
export function MemberGalleriesTab({ userId }: MemberGalleriesTabProps) {
  const router = useRouter();
  const { data, isLoading, error, refetch } = useGalleryList({
    owner_id: userId,
  });

  return (
    <div className="py-2">
      <AlbumGrid
        items={data?.items}
        isLoading={isLoading}
        error={error}
        onRetry={() => refetch()}
        onSelect={(id) =>
          router.push(`/app/photos?${new URLSearchParams({ gallery: id })}`)
        }
      />
    </div>
  );
}

export default MemberGalleriesTab;
