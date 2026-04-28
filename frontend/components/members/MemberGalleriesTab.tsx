"use client";
/**
 * @file components/members/MemberGalleriesTab.tsx
 * @brief Member profile galleries tab displaying owner's galleries.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import Box from "@mui/joy/Box";
import { GalleryGrid } from "@/components/galleries/GalleryGrid";
import type { ListGalleriesParams } from "@/lib/api/galleries";

export interface MemberGalleriesTabProps {
  userId: string;
}

export function MemberGalleriesTab({ userId }: MemberGalleriesTabProps) {
  const router = useRouter();

  const params: ListGalleriesParams = {
    owner_id: userId,
  };

  const handleSelect = (galleryId: string) => {
    router.push(`/app/galleries/${galleryId}`);
  };

  return (
    <Box sx={{ py: 2 }}>
      <GalleryGrid onSelect={handleSelect} params={params} />
    </Box>
  );
}

export default MemberGalleriesTab;
