"use client";
/**
 * @file components/galleries/galleries-page/GalleryMosaic.tsx
 * @brief Responsive grid of gallery cards with loading, error, empty states.
 */
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { GalleryCard } from "@/components/galleries/GalleryCard";
import type { Gallery } from "@/lib/api/galleries";

const GRID =
  "grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-5 lg:grid-cols-4 xl:grid-cols-5";

export interface GalleryMosaicProps {
  data: { items: Gallery[] } | undefined;
  isLoading: boolean;
  error: unknown;
  onSelect: (id: string) => void;
  onEmptyAction: () => void;
}

/**
 * @brief Gallery list body.
 * @param props query state plus select/empty-action callbacks
 * @return grid or state block
 */
export function GalleryMosaic({
  data,
  isLoading,
  error,
  onSelect,
  onEmptyAction,
}: GalleryMosaicProps) {
  if (error) {
    return (
      <EmptyState
        title="Couldn't load galleries"
        description={String(error)}
        action={
          <Button variant="secondary" onClick={() => window.location.reload()}>
            Retry
          </Button>
        }
      />
    );
  }
  if (isLoading) {
    return (
      <div className={GRID}>
        {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
          <Skeleton key={i} height={220} rounded="lg" />
        ))}
      </div>
    );
  }
  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        title="No galleries yet"
        description="Create one to share photos."
        action={<Button onClick={onEmptyAction}>Browse media</Button>}
      />
    );
  }
  return (
    <div className={GRID}>
      {data.items.map((g) => (
        <GalleryCard key={g.id} gallery={g} onSelect={onSelect} />
      ))}
    </div>
  );
}
