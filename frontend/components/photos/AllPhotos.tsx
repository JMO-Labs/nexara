"use client";
/**
 * @file components/photos/AllPhotos.tsx
 * @brief "All photos" view: uniform square grid of recent media from every
 *        visible album, group and post.
 */
import { Images } from "lucide-react";
import { EmptyState } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import type { HomeMediaItem } from "@/lib/api/home";

export interface AllPhotosProps {
  items: HomeMediaItem[] | undefined;
  isLoading: boolean;
  error: unknown;
  /** True when a search query is filtering the list. */
  filtered?: boolean;
  onOpen: (index: number) => void;
}

const GRID =
  "grid grid-cols-3 gap-2 md:grid-cols-4 md:gap-3 lg:grid-cols-5 xl:grid-cols-6";

/**
 * @brief All-photos grid with loading, error and empty states.
 * @param props see AllPhotosProps
 * @return grid or state block
 */
export function AllPhotos({
  items,
  isLoading,
  error,
  filtered,
  onOpen,
}: AllPhotosProps) {
  if (error) {
    return (
      <EmptyState
        title="Couldn't load photos"
        description={error instanceof Error ? error.message : String(error)}
      />
    );
  }
  if (isLoading || !items) {
    return (
      <div className={GRID} data-testid="photos-skeleton" aria-busy="true">
        {Array.from({ length: 12 }, (_, i) => (
          <div key={i} className="glass-item aspect-square rounded-2xl" />
        ))}
      </div>
    );
  }
  if (items.length === 0) {
    return (
      <EmptyState
        icon={Images}
        title={filtered ? "No matching photos" : "No photos yet"}
        description={
          filtered
            ? "Try a different search."
            : "Use Upload photos to add the first one."
        }
      />
    );
  }
  return (
    <ul className={GRID} aria-label="All photos">
      {items.map((it, i) => (
        <li key={`${it.source}-${it.source_id}-${it.media_id}`}>
          <button
            type="button"
            aria-label={`Open photo${it.source_title ? `: ${it.source_title}` : ""}`}
            onClick={() => onOpen(i)}
            className="bg-bg relative block aspect-square w-full overflow-hidden rounded-2xl outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <MediaThumb
              mediaId={it.media_id}
              alt={it.media.alt_text || it.source_title || "Photo"}
              zoomOnHover
            />
          </button>
        </li>
      ))}
    </ul>
  );
}

export default AllPhotos;
