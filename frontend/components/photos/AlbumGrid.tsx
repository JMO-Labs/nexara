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
  "glass-item relative block w-full overflow-hidden rounded-[28px] text-left text-ink outline-none transition-[flex-basis,height] duration-300 motion-reduce:transition-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:h-[380px]";

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
            className="glass-item h-28 rounded-[28px] md:h-[380px] md:flex-1"
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
              className={cn(CARD, open ? "h-72" : "h-28")}
            >
              {g.cover_media_id ? (
                <span className="absolute inset-0 block">
                  <MediaThumb
                    mediaId={g.cover_media_id}
                    alt={`${g.title} cover`}
                    objectPosition="50% 30%"
                  />
                </span>
              ) : (
                <span
                  data-testid="album-placeholder"
                  className="absolute inset-0 flex items-center justify-center bg-[color-mix(in_srgb,var(--nx-blue)_18%,transparent)]"
                >
                  <span className="glass-item flex size-14 items-center justify-center rounded-full">
                    <Images className="size-6" aria-hidden="true" />
                  </span>
                </span>
              )}
              <span className="glass-item absolute inset-x-3 bottom-3 flex flex-col gap-0.5 rounded-[20px] px-3 py-2">
                <span
                  className={cn(
                    "font-semibold",
                    open ? "text-lg" : "truncate text-sm",
                  )}
                >
                  {g.title}
                </span>
                <span className="text-xs text-muted">{count}</span>
                {open && (
                  <span className="mt-1 inline-flex w-fit rounded-full bg-surface-strong px-3 py-1 text-sm font-semibold text-bg">
                    Open album
                  </span>
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
