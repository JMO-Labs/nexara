"use client";
/**
 * @file components/galleries/Slideshow.tsx
 * @brief Full-screen TV slideshow: auto-advance, pause, keyboard, captions.
 */
import * as React from "react";
import { Pause, Play, X } from "lucide-react";
import { NsfwCover } from "@/components/feed/NsfwCover";
import { IconButton } from "@/components/ui";
import { useMemberProfile } from "@/hooks/useMembers";
import { API_BASE } from "@/lib/auth/session";
import type { GalleryItem } from "@/lib/api/galleries";

export const SLIDE_MS = 6000;
const fileUrl = (id: string) => `${API_BASE}/api/v1/media/${id}/file`;

export interface SlideshowProps {
  items: GalleryItem[];
  startIndex?: number;
  /** Called on Esc / close button. */
  onExit?: () => void;
  /** Whole gallery is NSFW. */
  nsfw?: boolean;
}

/** @brief Caption line: item caption plus uploader name. */
function Caption({ item }: { item: GalleryItem }) {
  const { data: member } = useMemberProfile(item.added_by);
  const by = member?.display_name ? `Added by ${member.display_name}` : "";
  if (!item.caption && !by) return null;
  return (
    <p className="absolute inset-x-0 bottom-0 bg-black/60 p-4 text-center text-lg text-white">
      {item.caption}
      {item.caption && by ? " · " : ""}
      {by}
    </p>
  );
}

/**
 * @brief Slideshow over gallery items. Space pauses, arrows navigate, Esc exits.
 * @param items gallery items in display order
 * @param startIndex first slide (default 0)
 * @param onExit exit handler
 * @return full-screen region
 */
export function Slideshow({
  items,
  startIndex = 0,
  onExit,
  nsfw,
}: SlideshowProps) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [index, setIndex] = React.useState(startIndex);
  const [paused, setPaused] = React.useState(false);
  const [videoIds, setVideoIds] = React.useState<Set<string>>(new Set());
  const [covered, setCovered] = React.useState(false);
  const n = items.length;
  const item = items[index];
  const isVideo = !!item && videoIds.has(item.media_id);

  const go = React.useCallback(
    (d: number) => n && setIndex((i) => (i + d + n) % n),
    [n],
  );

  React.useEffect(() => {
    const el = ref.current;
    el?.focus();
    try {
      void el?.requestFullscreen?.()?.catch(() => undefined);
    } catch {
      /* fullscreen is best effort */
    }
    return () => {
      try {
        if (document.fullscreenElement) void document.exitFullscreen();
      } catch {
        /* ignore */
      }
    };
  }, []);

  React.useEffect(() => {
    if (paused || isVideo || covered || n < 2) return;
    const t = setTimeout(() => go(1), SLIDE_MS);
    return () => clearTimeout(t);
  }, [paused, isVideo, covered, n, index, go]);

  React.useEffect(() => {
    if (n > 1) new Image().src = fileUrl(items[(index + 1) % n].media_id);
  }, [index, items, n]);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === " ") {
        e.preventDefault();
        setPaused((p) => !p);
      } else if (e.key === "Escape") onExit?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, onExit]);

  if (!item) return null;
  const label = item.caption || `Photo ${index + 1} of ${n}`;
  return (
    <div
      ref={ref}
      tabIndex={-1}
      role="region"
      aria-roledescription="slideshow"
      aria-label="Photo slideshow"
      className="fixed inset-0 z-[1500] flex items-center justify-center bg-black outline-none"
    >
      <NsfwCover
        nsfw={nsfw || item.is_nsfw}
        itemId={`media:${item.media_id}`}
        hideWhenCovered
        onCovered={setCovered}
        className="size-full"
      >
        {isVideo ? (
          <video
            key={item.id}
            src={fileUrl(item.media_id)}
            muted
            autoPlay
            aria-label={label}
            onEnded={() => go(1)}
            className="max-h-full max-w-full"
          />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element -- API media URL
          <img
            key={item.id}
            src={fileUrl(item.media_id)}
            alt={label}
            onError={() => setVideoIds((s) => new Set(s).add(item.media_id))}
            className="max-h-full max-w-full object-contain motion-safe:transition-opacity motion-safe:duration-500"
          />
        )}
      </NsfwCover>
      <Caption item={item} />
      <div className="absolute top-4 right-4 flex gap-2">
        <IconButton
          variant="glass"
          aria-label={paused ? "Play slideshow" : "Pause slideshow"}
          aria-pressed={paused}
          onClick={() => setPaused((p) => !p)}
        >
          {paused ? (
            <Play className="size-5" aria-hidden="true" />
          ) : (
            <Pause className="size-5" aria-hidden="true" />
          )}
        </IconButton>
        <IconButton
          variant="glass"
          aria-label="Exit slideshow"
          onClick={onExit}
        >
          <X className="size-5" aria-hidden="true" />
        </IconButton>
      </div>
      <p aria-live="polite" className="sr-only">
        {index + 1} of {n}
      </p>
    </div>
  );
}

export default Slideshow;
