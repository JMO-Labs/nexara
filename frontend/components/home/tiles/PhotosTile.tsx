"use client";
/**
 * @file components/home/tiles/PhotosTile.tsx
 * @brief Photos tile: 2x2 hero plus square thumbs from recent media.
 */
import Link from "next/link";
import { Image as ImageIcon } from "lucide-react";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { useHomeMedia } from "@/hooks/useHomeMedia";
import { mediaThumbUrl } from "@/lib/mediaUrl";
import { NsfwCover } from "@/components/feed/NsfwCover";
import { cn } from "@/lib/utils";

/**
 * @brief Photos tile.
 * @param props open/onToggle from the home page
 * @return HomeTile
 */
export function PhotosTile({ open, onToggle }: TileSlotProps) {
  const { data } = useHomeMedia({ limit: 7 });
  // 2x2 hero + 5 thumbs fill exactly three rows of a 3-col grid.
  const items = (data?.items ?? []).slice(0, 6);
  const more = (data?.items?.length ?? 0) > 6 || !!data?.next_cursor;
  return (
    <HomeTile
      id="photos"
      title="Photos"
      icon={ImageIcon}
      href="/app/photos"
      linkLabel="See galleries"
      summary={items.length ? `${items.length} new photos` : "Nothing new"}
      count={items.length}
      open={open}
      onToggle={onToggle}
      className="md:[grid-area:photos]"
    >
      {items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-6 text-center">
          <p className="text-sm text-[var(--nx-muted)]">No photos yet</p>
          <Link href="/app/photos" className="text-sm underline">
            Upload photos
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-1.5">
          {items.map((it, i) => (
            <div
              key={it.media_id}
              className={cn(
                "relative",
                i === 0 ? "col-span-2 row-span-2" : "aspect-square",
              )}
            >
              <NsfwCover
                nsfw={it.media.is_nsfw}
                itemId={`media:${it.media_id}`}
                compact
                hideWhenCovered
                className="absolute inset-0 rounded-xl"
              >
                <Link
                  href="/app/photos"
                  className="relative block h-full w-full overflow-hidden rounded-xl"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element -- API-served thumbnails, not optimizable by next/image */}
                  <img
                    src={mediaThumbUrl(it.media)}
                    alt={it.media.alt_text ?? ""}
                    loading="lazy"
                    className="h-full w-full object-cover"
                  />
                  {i === 5 && more ? (
                    <span className="absolute inset-0 flex items-center justify-center bg-black/45 text-lg font-medium text-white">
                      +
                    </span>
                  ) : null}
                </Link>
              </NsfwCover>
            </div>
          ))}
        </div>
      )}
    </HomeTile>
  );
}
