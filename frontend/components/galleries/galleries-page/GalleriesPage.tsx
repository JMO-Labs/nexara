"use client";
/**
 * @file components/galleries/galleries-page/GalleriesPage.tsx
 * @brief Galleries page composition: masthead, search/sort toolbar, featured
 *        spread, gallery grid, detail drawer and lightbox (?gallery= / ?item=).
 */
import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui";
import { GalleryCreateModal } from "@/components/galleries/GalleryCreateModal";
import { GallerySearchBar } from "@/components/galleries/GallerySearchBar";
import {
  GallerySortSelect,
  type SortOption,
} from "@/components/galleries/GallerySortSelect";
import { PageMasthead } from "@/components/layout/PageMasthead";
import { useGalleryList } from "@/hooks/useGalleries";
import type { ListGalleriesParams } from "@/lib/api/galleries";
import { FeaturedSpread } from "./FeaturedSpread";
import { GalleryDrawer } from "./GalleryDrawer";
import { GalleryMosaic } from "./GalleryMosaic";
import { LightboxConnected } from "./LightboxConnected";
import { SectionLabel } from "./SectionLabel";

/**
 * @brief Galleries page body.
 * @return page element
 */
export function GalleriesPage() {
  const router = useRouter();
  const params = useSearchParams();
  const galleryId = params.get("gallery");
  const itemIdx = params.get("item");
  const [createOpen, setCreateOpen] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState("");
  const [sort, setSort] = React.useState<SortOption>("recent");

  /** Push the current params after applying `mutate`. */
  const update = (mutate: (p: URLSearchParams) => void) => {
    const next = new URLSearchParams(params.toString());
    mutate(next);
    router.push(next.toString() ? `/app/galleries?${next}` : "/app/galleries");
  };
  const select = (id: string) => update((p) => p.set("gallery", id));
  const closeDrawer = () =>
    update((p) => {
      p.delete("gallery");
      p.delete("item");
    });
  const setItemIndex = (idx: number) =>
    update((p) => p.set("item", String(idx)));
  const closeItem = () => update((p) => p.delete("item"));

  const listParams: ListGalleriesParams = {
    q: searchQuery || undefined,
    sort,
  };
  const { data: featuredData } = useGalleryList({
    featured: true,
    sort: "popular",
  });
  const {
    data: listData,
    isLoading: listLoading,
    error: listError,
  } = useGalleryList(listParams);

  const featured = featuredData?.items ?? [];
  const totalCount = listData?.items.length ?? 0;

  return (
    <div className="w-full px-4 pb-10 md:px-8">
      <PageMasthead
        title="Galleries"
        meta={`${totalCount} ${totalCount === 1 ? "collection" : "collections"}`}
        right={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="size-4" aria-hidden="true" />
            New gallery
          </Button>
        }
      />

      <div className="bg-bg/80 sticky top-0 z-5 -mx-4 mb-8 flex flex-col gap-2 px-4 py-3 backdrop-blur md:-mx-8 md:mb-10 md:flex-row md:items-center md:justify-between md:px-8">
        <div className="min-w-0 flex-1">
          <GallerySearchBar onSearch={setSearchQuery} />
        </div>
        <GallerySortSelect sort={sort} onSortChange={setSort} />
      </div>

      {featured[0] && (
        <section className="mb-10 md:mb-14" aria-label="Featured galleries">
          <SectionLabel label="Featured" />
          <div className="mt-4">
            <FeaturedSpread
              hero={featured[0]}
              rail={featured.slice(1, 4)}
              onSelect={select}
            />
          </div>
        </section>
      )}

      <section aria-label="All galleries">
        <SectionLabel
          label={searchQuery ? "Results" : "All collections"}
          kicker={searchQuery ? `for "${searchQuery}"` : undefined}
        />
        <div className="mt-4">
          <GalleryMosaic
            data={listData}
            isLoading={listLoading}
            error={listError}
            onSelect={select}
            onEmptyAction={() => router.push("/app/media")}
          />
        </div>
      </section>

      <GalleryDrawer
        galleryId={galleryId}
        onClose={closeDrawer}
        onOpenItem={setItemIndex}
      />
      {galleryId && itemIdx !== null && (
        <LightboxConnected
          galleryId={galleryId}
          index={Number(itemIdx)}
          onClose={closeItem}
          onIndexChange={setItemIndex}
        />
      )}
      <GalleryCreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />
    </div>
  );
}

export default GalleriesPage;
