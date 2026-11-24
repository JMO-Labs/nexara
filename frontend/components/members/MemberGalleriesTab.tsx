"use client";
/**
 * @file components/members/MemberGalleriesTab.tsx
 * @brief Member profile albums: a responsive grid of album cards (cover,
 *        title, photo count) linking to the album in Photos.
 */
import * as React from "react";
import Link from "next/link";
import { Images } from "lucide-react";
import { NsfwCover } from "@/components/feed/NsfwCover";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { EmptyState, Skeleton, Button } from "@/components/ui";
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
  const { data, isLoading, error, refetch } = useGalleryList({
    owner_id: userId,
  });
  const items = data?.items ?? [];

  if (isLoading)
    return (
      <div
        className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
        aria-busy="true"
      >
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={220} rounded="lg" />
        ))}
      </div>
    );
  if (error)
    return (
      <EmptyState
        compact
        icon={Images}
        title="Couldn't load albums"
        action={
          <Button size="sm" onClick={() => void refetch()}>
            Try again
          </Button>
        }
      />
    );
  if (items.length === 0)
    return <EmptyState compact icon={Images} title="No albums yet" />;

  return (
    <ul
      className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
      aria-label="Albums"
    >
      {items.map((g) => (
        <li key={g.id}>
          <NsfwCover
            nsfw={g.is_nsfw}
            itemId={`gallery:${g.id}`}
            className="rounded-[24px]"
          >
            <Link
              href={`/app/photos?${new URLSearchParams({ gallery: g.id })}`}
              className="glass glass-lift group block overflow-hidden rounded-[24px] outline-none focus-visible:outline-2 focus-visible:outline-accent"
            >
              <span className="relative block aspect-[4/3] bg-[color-mix(in_srgb,var(--nx-blue)_18%,transparent)]">
                {g.cover_media_id ? (
                  <span className="absolute inset-0 block">
                    <MediaThumb
                      mediaId={g.cover_media_id}
                      alt=""
                      objectPosition="50% 30%"
                      zoomOnHover
                    />
                  </span>
                ) : (
                  <Images
                    aria-hidden
                    className="absolute inset-0 m-auto size-8 text-muted"
                  />
                )}
              </span>
              <span className="block px-4 py-3">
                <span className="block truncate font-medium">{g.title}</span>
                <span className="block text-xs text-muted">
                  {g.item_count} {g.item_count === 1 ? "photo" : "photos"}
                </span>
              </span>
            </Link>
          </NsfwCover>
        </li>
      ))}
    </ul>
  );
}

export default MemberGalleriesTab;
