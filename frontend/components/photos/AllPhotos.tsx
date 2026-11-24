"use client";
/**
 * @file components/photos/AllPhotos.tsx
 * @brief "All photos" view: uniform square grid of recent media from every
 *        visible album, group and post.
 */
import { Fragment } from "react";
import { format, isSameWeek, parseISO } from "date-fns";
import { Images } from "lucide-react";
import { EmptyState } from "@/components/ui";
import { NsfwCover } from "@/components/feed/NsfwCover";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { photoTitle } from "@/lib/photoTitle";
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
  "grid grid-cols-3 gap-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6";

/**
 * @brief Friendly group heading for a photo's date.
 * @param iso created_at timestamp
 * @return "This week" or the month and year, e.g. "March 2026"
 */
function groupLabel(iso: string): string {
  const d = parseISO(iso);
  return isSameWeek(d, new Date(), { weekStartsOn: 0 })
    ? "This week"
    : format(d, "MMMM yyyy");
}

/**
 * @brief Split items into consecutive date groups, keeping global indexes.
 * @param items photos in display order
 * @return groups with label and [item, index] pairs
 */
function groupItems(
  items: HomeMediaItem[],
): { label: string; entries: [HomeMediaItem, number][] }[] {
  const groups: { label: string; entries: [HomeMediaItem, number][] }[] = [];
  items.forEach((it, i) => {
    const label = groupLabel(it.media.created_at);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.entries.push([it, i]);
    else groups.push({ label, entries: [[it, i]] });
  });
  return groups;
}

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
          <div key={i} className="glass-item aspect-square rounded-[22px]" />
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
      {groupItems(items).map((group) => (
        <Fragment key={group.label}>
          <li className="col-span-full pt-2 first:pt-0">
            <h2 className="text-sm font-medium text-muted">{group.label}</h2>
          </li>
          {group.entries.map(([it, i]) => {
            const title = photoTitle(it);
            return (
              <li key={`${it.source}-${it.source_id}-${it.media_id}`}>
                <NsfwCover
                  nsfw={it.media.is_nsfw}
                  itemId={`media:${it.media_id}`}
                  className="rounded-[22px]"
                >
                  <button
                    type="button"
                    aria-label={`Open photo${title ? `: ${title}` : ""}`}
                    onClick={() => onOpen(i)}
                    className="group bg-bg relative block aspect-square w-full overflow-hidden rounded-[22px] outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  >
                    <MediaThumb
                      mediaId={it.media_id}
                      alt={it.media.alt_text || title || "Photo"}
                      zoomOnHover
                    />
                    {title && (
                      <span className="glass-item pointer-events-none absolute inset-x-2 bottom-2 hidden rounded-[18px] px-3 py-1.5 text-left text-xs font-medium text-ink group-hover:block group-focus-visible:block">
                        {title}
                      </span>
                    )}
                  </button>
                </NsfwCover>
              </li>
            );
          })}
        </Fragment>
      ))}
    </ul>
  );
}

export default AllPhotos;
