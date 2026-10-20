"use client";
/**
 * @file components/feed/PostMedia.tsx
 * @brief Media grid for post attachments (1 / 2 / 3+ layouts).
 */
import type { PostMedia as Media } from "@/lib/api/posts";

export interface PostMediaProps {
  media: Media[];
  onClick?: (index: number) => void;
}

function isImage(m: Media) {
  return m.mime_type.startsWith("image/");
}

/**
 * @brief Grid of up to four attachments with a "+N" overlay.
 * @param media attachments
 * @param onClick tile click handler (index)
 * @return grid element or null
 */
export function PostMedia({ media, onClick }: PostMediaProps) {
  if (!media || media.length === 0) return null;
  const visible = media.slice(0, 4);
  const overflow = Math.max(0, media.length - 4);

  return (
    <div
      className={`grid gap-2 overflow-hidden rounded-xl ${
        visible.length === 1 ? "grid-cols-1" : "grid-cols-2"
      }`}
    >
      {visible.map((m, i) => (
        <div
          key={m.id}
          onClick={() => onClick?.(i)}
          className={`relative overflow-hidden bg-bg ${
            onClick ? "cursor-pointer" : ""
          } ${visible.length === 1 ? "aspect-[16/10]" : "aspect-square"}`}
        >
          {isImage(m) ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={m.thumbnail_url ?? m.url}
              alt=""
              loading="lazy"
              className="size-full object-cover"
            />
          ) : (
            <video src={m.url} controls className="size-full object-cover" />
          )}
          {i === 3 && overflow > 0 ? (
            <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-2xl font-black text-white">
              +{overflow}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default PostMedia;
