"use client";
/**
 * @file components/members/MemberGalleriesTab.tsx
 * @brief Member profile galleries tab displaying owner's galleries.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { GalleryGrid } from "@/components/galleries/GalleryGrid";
import type { ListGalleriesParams } from "@/lib/api/galleries";

export interface MemberGalleriesTabProps {
  userId: string;
}

/**
 * @brief Grid of galleries owned by a member.
 * @param userId owner id filter
 * @return galleries grid
 */
export function MemberGalleriesTab({ userId }: MemberGalleriesTabProps) {
  const router = useRouter();
  const params: ListGalleriesParams = { owner_id: userId };

  return (
    <div className="py-2">
      <GalleryGrid
        onSelect={(id) => router.push(`/app/galleries/${id}`)}
        params={params}
      />
    </div>
  );
}

export default MemberGalleriesTab;
