"use client";
/**
 * @file components/home/widgets/MediaCarouselWidget.tsx
 * @brief Recent photos/videos from all visible groups in a one-up carousel.
 */
import * as React from "react";
import Link from "next/link";
import { useHomeMedia } from "@/hooks/useHomeMedia";
import { Carousel, EmptyState, Skeleton } from "@/components/ui";
import { API_BASE } from "@/lib/auth/session";
import { safeInternalLink } from "@/lib/safeLink";

/**
 * @brief Media widget body.
 * @return carousel, skeleton or empty state
 */
export function MediaCarouselWidget() {
  const { data, isLoading } = useHomeMedia({ limit: 12, scope: "all" });
  if (isLoading) return <Skeleton height={160} rounded="md" />;
  const items = (data?.items ?? []).filter((i) =>
    i.media.content_type.startsWith("image/"),
  );
  if (items.length === 0) {
    return (
      <EmptyState
        compact
        title="No media yet"
        description="Photos from your groups will appear here."
      />
    );
  }
  return (
    <Carousel
      ariaLabel="Recent media"
      showDots={false}
      slides={items.map((item) => {
        const href =
          item.source === "post"
            ? `/app/post/${item.source_id}`
            : `/app/galleries/${item.source_id}`;
        return (
          <Link
            key={item.media_id}
            href={safeInternalLink(href) ?? "/app"}
            aria-label={item.source_title ?? "Media item"}
            className="block h-40 overflow-hidden rounded-xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- user/external URL, unknown host for next/image */}
            <img
              src={`${API_BASE}/api/v1/media/${item.media.id}/${item.media.thumbnail_key ? "thumbnail" : "file"}`}
              alt={item.media.alt_text ?? item.source_title ?? ""}
              className="size-full object-cover"
            />
          </Link>
        );
      })}
    />
  );
}

export default MediaCarouselWidget;
