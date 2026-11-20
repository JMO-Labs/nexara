"use client";
/**
 * @file components/photos/PhotosPage.tsx
 * @brief Photos page: Albums (expand cards) and All photos views, upload
 *        panel, album drawer and lightbox (?view= / ?gallery= / ?item=).
 */
import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Upload } from "lucide-react";
import { Button } from "@/components/ui";
import {
  PageHeader,
  Panel,
  SearchField,
  Segmented,
  Toolbar,
} from "@/components/ui/page";
import { GalleryCreateModal } from "@/components/galleries/GalleryCreateModal";
import { Lightbox } from "@/components/galleries/Lightbox";
import { GalleryDrawer } from "@/components/galleries/galleries-page/GalleryDrawer";
import { LightboxConnected } from "@/components/galleries/galleries-page/LightboxConnected";
import { UploadZone } from "@/components/media/UploadZone";
import { useGalleryListInfinite } from "@/hooks/useGalleries";
import { useHomeMediaInfinite } from "@/hooks/useHomeMedia";
import { photoTitle } from "@/lib/photoTitle";
import type { GalleryItem } from "@/lib/api/galleries";
import { AlbumGrid } from "./AlbumGrid";
import { AllPhotos } from "./AllPhotos";

/** Prefix of every useHomeMedia query key (any limit/scope). */
const HOME_MEDIA_KEY = ["home-media"] as const;

type View = "albums" | "all";
type Sort = "recent" | "popular" | "oldest";

const VIEWS = [
  { value: "albums" as const, label: "Albums" },
  { value: "all" as const, label: "All photos" },
];
const SORTS = [
  { value: "recent" as const, label: "Recent" },
  { value: "popular" as const, label: "Popular" },
  { value: "oldest" as const, label: "Oldest" },
];

/**
 * @brief Photos page body.
 * @return page element
 */
export function PhotosPage() {
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const view: View = params.get("view") === "all" ? "all" : "albums";
  const galleryId = params.get("gallery");
  const itemIdx = params.get("item");
  const [createOpen, setCreateOpen] = React.useState(false);
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const [sort, setSort] = React.useState<Sort>("recent");
  const [lightbox, setLightbox] = React.useState<number | null>(null);

  const update = (mutate: (p: URLSearchParams) => void) => {
    const next = new URLSearchParams(params.toString());
    mutate(next);
    router.push(next.toString() ? `/app/photos?${next}` : "/app/photos");
  };
  const setView = (v: View) =>
    update((p) => {
      if (v === "all") p.set("view", "all");
      else p.delete("view");
      p.delete("gallery");
      p.delete("item");
    });
  const setItemIndex = (i: number) => update((p) => p.set("item", String(i)));

  const albums = useGalleryListInfinite({ q: search || undefined, sort });
  const media = useHomeMediaInfinite(60);
  const albumItems = React.useMemo(
    () => albums.data?.pages.flatMap((p) => p.items),
    [albums.data],
  );
  const needle = search.trim().toLowerCase();
  const photos = React.useMemo(
    () =>
      media.data?.pages
        .flatMap((p) => p.items)
        .filter(
          (m) =>
            !needle ||
            (m.source_title ?? "").toLowerCase().includes(needle) ||
            m.media.filename?.toLowerCase().includes(needle),
        ),
    [media.data, needle],
  );
  const lightboxItems: GalleryItem[] = (photos ?? []).map((m, i) => ({
    id: m.media_id,
    gallery_id: m.source_id ?? "",
    media_id: m.media_id,
    added_by: "",
    caption: photoTitle(m),
    position: i,
    created_at: m.media.created_at,
  }));

  return (
    <div className="pb-10">
      <PageHeader
        title="Photos"
        actions={
          <>
            <Button
              variant="glass"
              className="rounded-full"
              onClick={() => setCreateOpen(true)}
            >
              New album
            </Button>
            <Button
              aria-expanded={uploadOpen}
              onClick={() => setUploadOpen((o) => !o)}
            >
              <Upload className="size-4" aria-hidden="true" />
              Upload photos
            </Button>
          </>
        }
      />
      <Toolbar className="max-md:rounded-none max-md:border-0 max-md:bg-transparent max-md:p-0 max-md:shadow-none">
        <div className="order-2 min-w-0 flex-1 md:order-1 md:w-auto md:flex-none [&>*]:w-full md:[&>*]:w-auto">
          <Segmented
            label="View"
            options={VIEWS}
            value={view}
            onChange={setView}
          />
        </div>
        <div className="order-1 flex w-full min-w-0 md:order-2 md:w-auto md:flex-1">
          <SearchField
            value={search}
            onChange={setSearch}
            placeholder={view === "albums" ? "Search albums" : "Search photos"}
            label={view === "albums" ? "Search albums" : "Search photos"}
            debounceMs={250}
          />
        </div>
        {view === "albums" && (
          <div className="glass-item relative order-3 inline-flex shrink-0 items-center rounded-full md:ml-auto">
            <select
              aria-label="Sort albums"
              value={sort}
              onChange={(e) => setSort(e.target.value as Sort)}
              className="h-8 cursor-pointer appearance-none rounded-full bg-transparent pr-8 pl-3.5 text-sm text-ink outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              {SORTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {`Sort: ${o.label}`}
                </option>
              ))}
            </select>
            <ChevronDown
              className="pointer-events-none absolute right-3 size-4 text-muted"
              aria-hidden="true"
            />
          </div>
        )}
      </Toolbar>

      {uploadOpen && (
        <Panel title="Upload photos" className="mt-4">
          <UploadZone
            onComplete={() => {
              qc.invalidateQueries({ queryKey: HOME_MEDIA_KEY });
              if (view !== "all") setView("all");
            }}
          />
        </Panel>
      )}

      <div className="mt-4">
        {view === "albums" ? (
          <>
            <AlbumGrid
              items={albumItems}
              isLoading={albums.isLoading}
              error={albums.error}
              onRetry={() => albums.refetch()}
              onSelect={(id) => update((p) => p.set("gallery", id))}
              empty={
                <Button onClick={() => setCreateOpen(true)}>New album</Button>
              }
            />
            {albums.hasNextPage && (
              <div className="mt-6 flex justify-center">
                <Button
                  variant="secondary"
                  onClick={() => albums.fetchNextPage()}
                  disabled={albums.isFetchingNextPage}
                >
                  {albums.isFetchingNextPage ? "Loading…" : "Load more"}
                </Button>
              </div>
            )}
          </>
        ) : (
          <>
            <AllPhotos
              items={photos}
              isLoading={media.isLoading}
              error={media.error}
              filtered={!!needle}
              onOpen={setLightbox}
            />
            {media.hasNextPage && (
              <div className="mt-4 flex justify-center">
                <Button
                  variant="secondary"
                  onClick={() => media.fetchNextPage()}
                  disabled={media.isFetchingNextPage}
                >
                  {media.isFetchingNextPage ? "Loading…" : "Load more"}
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {view === "all" && lightbox !== null && lightboxItems.length > 0 && (
        <Lightbox
          items={lightboxItems}
          index={Math.min(lightbox, lightboxItems.length - 1)}
          onClose={() => setLightbox(null)}
          onIndexChange={setLightbox}
        />
      )}
      <GalleryDrawer
        galleryId={galleryId}
        onClose={() =>
          update((p) => {
            p.delete("gallery");
            p.delete("item");
          })
        }
        onOpenItem={setItemIndex}
        suspended={itemIdx !== null}
      />
      {galleryId && itemIdx !== null && (
        <LightboxConnected
          galleryId={galleryId}
          index={Number(itemIdx)}
          onClose={() => update((p) => p.delete("item"))}
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

export default PhotosPage;
