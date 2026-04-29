"use client";
/**
 * @file components/home/widgets/MediaCarouselWidget.tsx
 * @brief Media carousel widget — fetches aggregated home media and renders
 *        the Carousel primitive. Each slide links to the source post/gallery.
 */
import * as React from "react";
import Link from "next/link";
import { useHomeMedia } from "@/hooks/useHomeMedia";
import { Carousel } from "@/components/ui/Carousel";
import { EmptyState, Skeleton } from "@/components/ui";
import type { WidgetContext } from "@/lib/widgets/registry";

export function MediaCarouselWidget(_: WidgetContext) {
  const { data, isLoading } = useHomeMedia(24);

  if (isLoading) {
    return <Skeleton height={220} rounded="md" />;
  }

  const items = data?.items ?? [];

  if (items.length === 0) {
    return (
      <EmptyState
        title="No media yet"
        description="Media from your groups will appear here."
      />
    );
  }

  const slides = items.map((item) => {
    const isImage =
      item.media.content_type.startsWith("image/");
    const href =
      item.source === "post"
        ? `/app/post/${item.source_id}`
        : `/app/galleries/${item.source_id}`;

    return (
      <Link
        key={item.media_id}
        href={href}
        aria-label={item.source_title ?? "Media item"}
        className="block relative w-full overflow-hidden rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)]"
        style={{ aspectRatio: "16/9" }}
      >
        {isImage ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={item.media.thumbnail_key ?? item.media.storage_key}
            alt={item.media.alt_text ?? item.source_title ?? ""}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-neutral-100 dark:bg-neutral-800">
            <span className="text-neutral-500 text-sm">
              {item.source_title ?? "Media"}
            </span>
          </div>
        )}
        {item.source_title && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-3 py-2">
            <p className="text-white text-xs font-medium truncate">
              {item.source_title}
            </p>
          </div>
        )}
      </Link>
    );
  });

  return (
    <Carousel
      slides={slides}
      slidesPerView={3}
      loop
      ariaLabel="Media from your groups"
      showArrows
      showDots
    />
  );
}

export default MediaCarouselWidget;
