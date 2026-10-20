"use client";
/**
 * @file components/galleries/galleries-page/FeaturedSpread.tsx
 * @brief Featured galleries: one large cover tile plus up to three smaller.
 */
import { Badge } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { cn } from "@/lib/utils";
import type { Gallery } from "@/lib/api/galleries";

interface TileProps {
  gallery: Gallery;
  onSelect: (id: string) => void;
  large?: boolean;
}

/**
 * @brief Clickable cover tile with a title overlay.
 * @param gallery gallery to show
 * @param onSelect called with the gallery id
 * @param large use the dominant size
 * @return button element
 */
function FeaturedTile({ gallery, onSelect, large }: TileProps) {
  const pieces = `${gallery.item_count} ${gallery.item_count === 1 ? "piece" : "pieces"}`;
  return (
    <button
      type="button"
      onClick={() => onSelect(gallery.id)}
      className={cn(
        "group bg-surface focus-visible:outline-accent relative block w-full overflow-hidden rounded-[1.25rem] text-left focus-visible:outline-2 focus-visible:outline-offset-2",
        large ? "min-h-[360px] md:row-span-3" : "min-h-[160px]",
      )}
    >
      <MediaThumb
        mediaId={gallery.cover_media_id}
        alt={`${gallery.title} cover`}
        zoomOnHover
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/70"
      />
      {large && gallery.is_featured && (
        <Badge tone="sun" className="absolute top-4 left-4">
          Featured
        </Badge>
      )}
      <div className="absolute inset-x-0 bottom-0 p-4 text-white md:p-6">
        <h3
          className={cn(
            "font-black tracking-tight",
            large ? "text-3xl md:text-4xl" : "truncate text-lg",
          )}
        >
          {gallery.title}
        </h3>
        <p className="mt-1 text-xs text-white/80">{pieces}</p>
      </div>
    </button>
  );
}

/**
 * @brief Featured grid.
 * @param hero dominant gallery
 * @param rail smaller galleries beside it
 * @param onSelect called with the chosen gallery id
 * @return grid element
 */
export function FeaturedSpread({
  hero,
  rail,
  onSelect,
}: {
  hero: Gallery;
  rail: Gallery[];
  onSelect: (id: string) => void;
}) {
  return (
    <div className="grid gap-3 md:min-h-[540px] md:grid-cols-[7fr_5fr] md:grid-rows-3 md:gap-5">
      <FeaturedTile gallery={hero} onSelect={onSelect} large />
      {rail.map((g) => (
        <FeaturedTile key={g.id} gallery={g} onSelect={onSelect} />
      ))}
    </div>
  );
}
