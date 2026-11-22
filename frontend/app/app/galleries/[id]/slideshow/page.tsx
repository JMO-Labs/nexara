"use client";
/**
 * @file app/app/galleries/[id]/slideshow/page.tsx
 * @brief Full-screen slideshow of one gallery (for TVs).
 */
import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { EmptyState, Skeleton } from "@/components/ui";
import { Slideshow } from "@/components/galleries/Slideshow";
import { useGalleryItems } from "@/hooks/useGalleries";

/**
 * @brief Load the gallery's items and play them.
 * @return slideshow, skeleton or empty state
 */
export default function SlideshowPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: items, isLoading, isError } = useGalleryItems(id);
  const exit = React.useCallback(
    () => router.push(`/app/photos?gallery=${encodeURIComponent(id)}`),
    [router, id],
  );
  if (isLoading) return <Skeleton height={300} />;
  if (isError)
    return (
      <EmptyState
        title="This album isn't available"
        description="It may be private, or it was removed."
      />
    );
  if (!items?.length)
    return (
      <EmptyState title="Nothing to show" description="Add photos first." />
    );
  return <Slideshow items={items} onExit={exit} />;
}
