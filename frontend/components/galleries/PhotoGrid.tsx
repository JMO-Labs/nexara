"use client";
/**
 * @file components/galleries/PhotoGrid.tsx
 * @brief Square thumbnail grid for a list of media ids that opens the
 *        Lightbox (with its tag bar).
 */
import * as React from "react";
import { NsfwCover } from "@/components/feed/NsfwCover";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { Lightbox } from "@/components/galleries/Lightbox";

/**
 * @brief Photo grid.
 * @param mediaIds photos in order
 * @return grid
 */
export function PhotoGrid({
  mediaIds,
  nsfwIds,
}: {
  mediaIds: string[];
  /** Ids to cover (adults); omitted when the source has no NSFW info. */
  nsfwIds?: readonly string[];
}) {
  const [open, setOpen] = React.useState<number | null>(null);
  return (
    <>
      <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4 xl:grid-cols-5">
        {mediaIds.map((id, i) => (
          <li key={id}>
            <NsfwCover
              nsfw={nsfwIds?.includes(id)}
              itemId={`media:${id}`}
              className="rounded-2xl"
            >
              <button
                type="button"
                onClick={() => setOpen(i)}
                aria-label={`Open photo ${i + 1}`}
                className="relative block aspect-square w-full overflow-hidden rounded-2xl"
              >
                <span className="absolute inset-0 block">
                  <MediaThumb mediaId={id} alt="" zoomOnHover />
                </span>
              </button>
            </NsfwCover>
          </li>
        ))}
      </ul>
      {open !== null && (
        <Lightbox
          items={mediaIds.map((id, i) => ({
            id,
            gallery_id: "",
            media_id: id,
            added_by: "",
            caption: null,
            position: i,
            created_at: "",
            is_nsfw: nsfwIds?.includes(id),
          }))}
          index={open}
          onIndexChange={setOpen}
          onClose={() => setOpen(null)}
        />
      )}
    </>
  );
}
