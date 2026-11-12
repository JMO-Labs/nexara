"use client";
/**
 * @file components/subgroups/hub/MediaTab.tsx
 * @brief Media tab: grid of media from posts, galleries, and events with source filtering.
 */
import * as React from "react";
import { Badge, EmptyState, Skeleton } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { useSubgroupMedia } from "@/hooks/useSubgroupMedia";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface MediaTabProps {
  subgroup: SubgroupDetail;
}

type Source = "all" | "post" | "gallery" | "event";

export function MediaTab({ subgroup }: MediaTabProps) {
  const [source, setSource] = React.useState<Source>("all");

  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    error,
  } = useSubgroupMedia({
    slug: subgroup.slug,
    source,
    limit: 60,
  });

  const items = data?.pages.flatMap((p) => p.items) ?? [];

  // Source filter chips
  const sourceOptions: { label: string; value: Source }[] = [
    { label: "All", value: "all" },
    { label: "Posts", value: "post" },
    { label: "Galleries", value: "gallery" },
    { label: "Events", value: "event" },
  ];

  const sentinelRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!sentinelRef.current || !hasNextPage || isFetchingNextPage || isLoading)
      return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 },
    );

    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, isLoading, fetchNextPage]);

  if (error) {
    return (
      <EmptyState title="Couldn't load media" description={String(error)} />
    );
  }

  const grid = "grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4";

  return (
    <div className="flex flex-col gap-4">
      <div
        className="flex flex-wrap gap-2"
        role="group"
        aria-label="Media source"
      >
        {sourceOptions.map((opt) => (
          <button
            key={opt.value}
            type="button"
            aria-pressed={source === opt.value}
            onClick={() => setSource(opt.value)}
            className="min-h-11 rounded-full outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <Badge
              tone={source === opt.value ? "accent" : "neutral"}
              className="px-4 py-2 text-sm"
            >
              {opt.label}
            </Badge>
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className={grid}>
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} height="auto" className="aspect-square" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          title="No media yet"
          description={
            source === "all"
              ? "Share photos and videos from posts, galleries, and events."
              : `No media from ${source}s yet.`
          }
        />
      ) : (
        <>
          <div className={grid}>
            {items.map((item) => (
              <div
                key={item.media_id}
                role="button"
                tabIndex={0}
                aria-label={`${item.source_title || "media"}`}
                className="relative aspect-square overflow-hidden rounded-xl bg-surface transition-opacity hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                <MediaThumb
                  mediaId={item.media_id}
                  alt={item.media.alt_text || `${item.source_title || "Media"}`}
                  zoomOnHover
                />
              </div>
            ))}
          </div>
          {isFetchingNextPage && (
            <div className="flex justify-center py-4">
              <Skeleton width={40} height={40} />
            </div>
          )}
          <div ref={sentinelRef} className="h-px" />
        </>
      )}
    </div>
  );
}

export default MediaTab;
