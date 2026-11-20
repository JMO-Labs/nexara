"use client";
/**
 * @file components/photos/AlbumGrid.tsx
 * @brief Expand-image-cards album list: tall cover cards that widen on
 *        hover/focus (desktop) or accordion vertically (phone).
 */
import * as React from "react";
import { Images } from "lucide-react";
import { Button, EmptyState } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { useIsMobile } from "@/hooks/useIsMobile";
import { cn } from "@/lib/utils";
import type { Gallery } from "@/lib/api/galleries";

export interface AlbumGridProps {
  items: Gallery[] | undefined;
  isLoading?: boolean;
  error?: unknown;
  onSelect: (id: string) => void;
  onRetry?: () => void;
  /** Action node shown in the empty state. */
  empty?: React.ReactNode;
}

const ROW = "flex flex-col gap-3 md:flex-row md:flex-wrap md:items-stretch";
const CARD =
  "glass-item relative block w-full overflow-hidden rounded-[28px] text-left text-white outline-none transition-[flex-basis,height] duration-300 motion-reduce:transition-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:h-[380px]";

/**
 * @brief Album card list with loading, error and empty states.
 * @param props see AlbumGridProps
 * @return list of album cards or a state block
 */
export function AlbumGrid({
  items,
  isLoading,
  error,
  onSelect,
  onRetry,
  empty,
}: AlbumGridProps) {
  const mobile = useIsMobile();
  const [active, setActive] = React.useState<string | null>(null);

  if (error) {
    return (
      <EmptyState
        title="Couldn't load albums"
        description={error instanceof Error ? error.message : String(error)}
        action={
          onRetry && (
            <Button variant="secondary" onClick={onRetry}>
              Retry
            </Button>
          )
        }
      />
    );
  }
  if (isLoading || !items) {
    return (
      <div className={ROW} data-testid="album-skeleton" aria-busy="true">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="glass-item h-24 rounded-[28px] md:h-[380px] md:flex-1"
          />
        ))}
      </div>
    );
  }
  if (items.length === 0) {
    return (
      <EmptyState
        icon={Images}
        title="No albums yet"
        description="Create one to share photos."
        action={empty}
      />
    );
  }
  return (
    <ul className={ROW} aria-label="Albums">
      {items.map((g) => {
        const open = active === g.id;
        const count = `${g.item_count} ${g.item_count === 1 ? "photo" : "photos"}`;
        return (
          <li
            key={g.id}
            className={cn(
              "list-none transition-[flex-basis] duration-300 motion-reduce:transition-none md:min-w-[120px]",
              open
                ? "md:basis-[360px] md:grow-[2]"
                : "md:basis-[170px] md:grow",
            )}
          >
            <button
              type="button"
              aria-label={g.title}
              aria-expanded={open}
              onMouseEnter={() => !mobile && setActive(g.id)}
              onMouseLeave={() =>
                !mobile && setActive((a) => (a === g.id ? null : a))
              }
              onFocus={() => !mobile && setActive(g.id)}
              onBlur={() =>
                !mobile && setActive((a) => (a === g.id ? null : a))
              }
              onClick={() => {
                if (mobile && !open) setActive(g.id);
                else onSelect(g.id);
              }}
              className={cn(CARD, open ? "h-72" : "h-24")}
            >
              <span className="bg-bg absolute inset-0 block">
                <MediaThumb
                  mediaId={g.cover_media_id}
                  alt={`${g.title} cover`}
                />
              </span>
              <span className="absolute inset-x-0 bottom-0 flex flex-col gap-1 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-4 pt-12">
                <span
                  className={cn(
                    "font-semibold",
                    open ? "text-xl" : "truncate text-sm",
                  )}
                >
                  {g.title}
                </span>
                {open && (
                  <>
                    <span className="text-sm text-white/85">{count}</span>
                    <span className="mt-1 inline-flex w-fit rounded-full bg-white px-3 py-1 text-sm font-semibold text-black">
                      Open album
                    </span>
                  </>
                )}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export default AlbumGrid;
