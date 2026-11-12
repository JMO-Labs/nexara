"use client";
/**
 * @file components/media/MediaSelector.tsx
 * @brief Modal with Upload / Gallery / URL tabs returning a SelectedMedia.
 */
import * as React from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Image as ImageIcon, Link as LinkIcon, Upload } from "lucide-react";
import { Modal, Button, Tabs, TabList, Tab, TabPanel } from "@/components/ui";
import { UploadZone } from "./UploadZone";
import {
  listMedia,
  mediaFileUrl,
  mediaThumbUrl,
  type MediaItem,
} from "@/lib/api/media";

export interface SelectedMedia {
  mediaId: string | null;
  url: string;
  alt: string;
}

export interface MediaSelectorProps {
  open: boolean;
  onClose: () => void;
  onSelect: (media: SelectedMedia) => void;
}

const URL_RE = /^https?:\/\//;

const fromItem = (m: MediaItem): SelectedMedia => ({
  mediaId: m.id,
  url: mediaFileUrl(m.id),
  alt: m.filename,
});

function Gallery({ onPick }: { onPick: (m: MediaItem) => void }) {
  const q = useInfiniteQuery({
    queryKey: ["media", "selector", 20] as const,
    queryFn: ({ pageParam }) => listMedia(pageParam, 20),
    initialPageParam: null as string | null,
    getNextPageParam: (p) => p.next_cursor,
  });
  const sentinel = React.useRef<HTMLDivElement>(null);
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = q;
  React.useEffect(() => {
    const el = sentinel.current;
    if (!el || !hasNextPage || typeof IntersectionObserver === "undefined")
      return;
    const io = new IntersectionObserver((e) => {
      if (e[0]?.isIntersecting && !isFetchingNextPage) void fetchNextPage();
    });
    io.observe(el);
    return () => io.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  if (q.isError)
    return (
      <p role="alert" className="text-sm text-destructive">
        Could not load media.
      </p>
    );
  if (!q.isLoading && items.length === 0)
    return <p className="text-sm text-muted">No media yet.</p>;
  return (
    <div className="max-h-80 overflow-y-auto">
      <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {items.map((m) => (
          <li key={m.id}>
            <button
              type="button"
              aria-label={m.filename}
              onClick={() => onPick(m)}
              className="aspect-square min-h-11 w-full overflow-hidden rounded-lg focus-visible:ring-2 focus-visible:ring-accent"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={mediaThumbUrl(m.id)}
                alt=""
                loading="lazy"
                className="h-full w-full object-cover"
              />
            </button>
          </li>
        ))}
      </ul>
      <div ref={sentinel} aria-hidden className="h-1" />
      {hasNextPage && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="mt-2"
          disabled={isFetchingNextPage}
          onClick={() => void fetchNextPage()}
        >
          Load more
        </Button>
      )}
    </div>
  );
}

function UrlTab({ onSubmit }: { onSubmit: (url: string) => void }) {
  const [value, setValue] = React.useState("");
  const [checked, setChecked] = React.useState(false);
  const [broken, setBroken] = React.useState(false);
  const valid = URL_RE.test(value.trim());
  const showError = checked && !valid;
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (valid) onSubmit(value.trim());
      }}
    >
      <label htmlFor="media-url" className="text-sm font-semibold">
        Image URL
      </label>
      <input
        id="media-url"
        type="url"
        value={value}
        placeholder="https://example.com/image.png"
        aria-invalid={showError}
        onChange={(e) => {
          setValue(e.target.value);
          setBroken(false);
        }}
        onBlur={() => setChecked(true)}
        className="min-h-11 rounded-lg border border-current/30 bg-surface px-3"
      />
      {showError && (
        <p role="alert" className="text-sm text-destructive">
          URL must start with http:// or https://
        </p>
      )}
      {valid && (
        <div className="flex h-32 w-32 items-center justify-center overflow-hidden rounded-lg bg-bg">
          {broken ? (
            <ImageIcon aria-label="Preview unavailable" />
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={value.trim()}
              alt="Preview"
              onError={() => setBroken(true)}
              className="h-full w-full object-cover"
            />
          )}
        </div>
      )}
      <Button type="submit" disabled={!valid} className="min-h-11 self-start">
        Use URL
      </Button>
    </form>
  );
}

/**
 * @brief Media picker dialog. Closes after a selection.
 * @param props see MediaSelectorProps
 * @return modal element
 */
export function MediaSelector({ open, onClose, onSelect }: MediaSelectorProps) {
  const pick = (m: SelectedMedia) => {
    onSelect(m);
    onClose();
  };
  return (
    <Modal open={open} onClose={onClose} title="Select media" size="lg">
      <Tabs defaultValue="upload">
        <TabList aria-label="Media source">
          <Tab value="upload">
            <Upload aria-hidden className="mr-1 inline h-4 w-4" />
            Upload
          </Tab>
          <Tab value="gallery">
            <ImageIcon aria-hidden className="mr-1 inline h-4 w-4" />
            Gallery
          </Tab>
          <Tab value="url">
            <LinkIcon aria-hidden className="mr-1 inline h-4 w-4" />
            URL
          </Tab>
        </TabList>
        <TabPanel value="upload">
          <UploadZone onComplete={(m) => pick(fromItem(m))} />
        </TabPanel>
        <TabPanel value="gallery">
          <Gallery onPick={(m) => pick(fromItem(m))} />
        </TabPanel>
        <TabPanel value="url">
          <UrlTab onSubmit={(url) => pick({ mediaId: null, url, alt: url })} />
        </TabPanel>
      </Tabs>
    </Modal>
  );
}

export default MediaSelector;
