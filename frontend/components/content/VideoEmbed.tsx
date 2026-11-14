"use client";
/**
 * @file components/content/VideoEmbed.tsx
 * @brief Click-to-play video embed (YouTube, Vimeo, Twitch, PeerTube, Dailymotion).
 */
import * as React from "react";
import { Play, Loader2 } from "lucide-react";
import { API_BASE } from "@/lib/auth/session";
import type { LinkPreview } from "@/lib/api/posts";

export interface VideoEmbedProps {
  preview: LinkPreview;
  thumbnail?: string;
}

const SAFE_ID = /^[A-Za-z0-9_-]+$/;

/**
 * @brief Build the provider embed URL.
 * @param preview link preview with provider_type/provider_id
 * @return embed URL, or null if unsupported or the id is unsafe
 */
export function embedUrl(preview: LinkPreview): string | null {
  const id = preview.provider_id;
  if (!id || !SAFE_ID.test(id)) return null;
  switch (preview.provider_type) {
    case "youtube":
      return `https://www.youtube.com/embed/${id}?rel=0`;
    case "vimeo":
      return `https://player.vimeo.com/video/${id}`;
    case "twitch":
      return /^\d+$/.test(id)
        ? `https://player.twitch.tv/?video=${id}`
        : `https://player.twitch.tv/?channel=${id}`;
    case "dailymotion":
      return `https://www.dailymotion.com/embed/video/${id}`;
    case "peertube": {
      try {
        const o = new URL(preview.og_image || preview.url);
        if (o.protocol !== "https:" && o.protocol !== "http:") return null;
        return `${o.origin}/videos/embed/${id}`;
      } catch {
        return null;
      }
    }
    default:
      return null;
  }
}

/**
 * @brief Thumbnail with play button; swaps to a sandboxed iframe on click.
 * @param preview link preview data
 * @param thumbnail fallback thumbnail URL
 * @return embed element, or null when no embed URL can be built
 */
export function VideoEmbed({ preview, thumbnail }: VideoEmbedProps) {
  const [active, setActive] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const src = embedUrl(preview);
  if (!src) return null;
  const thumb = preview.og_image
    ? `${API_BASE}/api/v1/link-previews/${encodeURIComponent(preview.id)}/image`
    : thumbnail;
  const label = preview.og_title || "Video preview";

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-lg border border-gray-300 bg-black md:max-w-[600px]">
      {active ? (
        <>
          {loading ? (
            <Loader2
              className="absolute left-1/2 top-1/2 size-8 -translate-x-1/2 -translate-y-1/2 animate-spin text-white"
              aria-hidden="true"
            />
          ) : null}
          <iframe
            src={src}
            title={label}
            sandbox="allow-scripts allow-same-origin allow-presentation"
            allowFullScreen
            loading="lazy"
            referrerPolicy="no-referrer"
            onLoad={() => setLoading(false)}
            className="size-full border-0"
          />
        </>
      ) : (
        <>
          {thumb ? (
            // eslint-disable-next-line @next/next/no-img-element -- user/external URL, unknown host for next/image
            <img
              src={thumb}
              alt={label}
              loading="lazy"
              className="size-full object-cover"
            />
          ) : null}
          <button
            type="button"
            onClick={() => setActive(true)}
            aria-label={`Video: ${preview.provider_type}, click to play`}
            className="absolute inset-0 flex cursor-pointer items-center justify-center bg-black/20 focus-visible:outline-2 focus-visible:-outline-offset-4 focus-visible:outline-white"
          >
            <span className="flex size-16 items-center justify-center rounded-full bg-black/70 text-white">
              <Play className="size-12" aria-hidden="true" />
            </span>
          </button>
        </>
      )}
    </div>
  );
}

export default VideoEmbed;
