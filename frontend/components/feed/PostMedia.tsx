"use client";
/**
 * @file components/feed/PostMedia.tsx
 * @brief Media grid for post attachments (1 / 2 / 3+ layouts).
 */
import { AudioPlayer } from "@/components/audio/AudioPlayer";
import { ReportButton } from "@/components/common/ReportButton";
import { NsfwCover } from "./NsfwCover";
import type { PostMedia as Media } from "@/lib/api/posts";

export interface PostMediaProps {
  media: Media[];
  onClick?: (index: number) => void;
  /** Show a per-tile Report action (viewer is not the owner). */
  canReport?: boolean;
  /** Parent already covers the whole post; skip per-tile covers. */
  skipCover?: boolean;
}

function isImage(m: Media) {
  return m.mime_type.startsWith("image/");
}

const isAudio = (m: Media) => m.mime_type.startsWith("audio/");

/**
 * @brief Grid of up to four attachments with a "+N" overlay.
 * @param media attachments
 * @param onClick tile click handler (index)
 * @param canReport show Report on each tile
 * @return grid element or null
 */
export function PostMedia({
  media,
  onClick,
  canReport,
  skipCover,
}: PostMediaProps) {
  if (!media || media.length === 0) return null;
  const audio = media.filter(isAudio);
  const visual = media.filter((m) => !isAudio(m));
  const visible = visual.slice(0, 4);
  const overflow = Math.max(0, visual.length - 4);

  return (
    <>
      {audio.length > 0 && (
        <div className="mb-2 flex flex-col gap-2">
          {audio.map((m) => (
            <AudioPlayer key={m.id} src={m.url} label="Voice note" />
          ))}
        </div>
      )}
      {visual.length > 0 && (
        <div
          className={`grid gap-2 overflow-hidden rounded-xl ${
            visible.length === 1 ? "grid-cols-1" : "grid-cols-2"
          }`}
        >
          {visible.map((m, i) => (
            <div
              key={m.id}
              onClick={() => onClick?.(i)}
              className={`group relative overflow-hidden bg-bg ${
                onClick ? "cursor-pointer" : ""
              } ${visible.length === 1 ? "aspect-[16/10]" : "aspect-square"}`}
            >
              <NsfwCover
                nsfw={m.is_nsfw && !skipCover}
                itemId={`media:${m.id}`}
                className="size-full"
              >
                {isImage(m) ? (
                  // eslint-disable-next-line @next/next/no-img-element -- user/external URL, unknown host for next/image
                  <img
                    src={m.thumbnail_url ?? m.url}
                    alt=""
                    loading="lazy"
                    className="size-full object-cover"
                  />
                ) : (
                  <video
                    src={m.url}
                    controls
                    className="size-full object-cover"
                  />
                )}
              </NsfwCover>
              {i === 3 && overflow > 0 ? (
                <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-2xl font-black text-white">
                  +{overflow}
                </div>
              ) : null}
              {canReport ? (
                <div
                  className="hover-only absolute right-2 top-2 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ReportButton
                    targetType="media"
                    targetId={m.id}
                    className="inline-flex items-center gap-1 rounded-full bg-black/50 px-2.5 py-1 text-xs font-medium text-white backdrop-blur-sm outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                  />
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default PostMedia;
