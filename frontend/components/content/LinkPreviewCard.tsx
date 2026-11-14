"use client";
/**
 * @file components/content/LinkPreviewCard.tsx
 * @brief Open Graph link preview card (image, title, description, site).
 */
import * as React from "react";
import { Link as LinkIcon } from "lucide-react";
import { API_BASE } from "@/lib/auth/session";
import type { LinkPreview } from "@/lib/api/posts";

export interface LinkPreviewCardProps {
  preview: LinkPreview;
  onClick?: () => void;
}

const clip = (s: string, n: number) =>
  s.length > n ? `${s.slice(0, n - 1)}…` : s;

/** @brief True only for http(s) URLs (blocks javascript:, data:, etc.). */
const isHttpUrl = (url: string): boolean => {
  try {
    return ["http:", "https:"].includes(new URL(url).protocol);
  } catch {
    return false;
  }
};

/**
 * @brief Clickable preview card; opens the URL in a new tab.
 * @param preview link preview data
 * @param onClick optional callback (e.g. analytics)
 * @return anchor element, or null for non-http(s) URLs
 */
export function LinkPreviewCard({ preview, onClick }: LinkPreviewCardProps) {
  const [imgFailed, setImgFailed] = React.useState(false);
  const title = preview.og_title ? clip(preview.og_title, 100) : preview.url;
  const desc = preview.og_description
    ? clip(preview.og_description, 200)
    : null;
  const showImg = !!preview.og_image && !imgFailed;
  if (!isHttpUrl(preview.url)) return null;

  return (
    <a
      href={preview.url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={() => onClick?.()}
      className="flex w-full cursor-pointer flex-col overflow-hidden rounded-lg border border-gray-300 bg-[var(--nx-surface)] no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--nx-ink)] md:max-w-[500px]"
    >
      <div className="aspect-video w-full bg-black/5">
        {showImg ? (
          // eslint-disable-next-line @next/next/no-img-element -- user/external URL, unknown host for next/image
          <img
            src={`${API_BASE}/api/v1/link-previews/${encodeURIComponent(preview.id)}/image`}
            alt={preview.og_title || "Link preview"}
            loading="lazy"
            onError={() => setImgFailed(true)}
            className="size-full object-cover"
          />
        ) : (
          <div
            data-testid="link-preview-fallback"
            className="flex size-full items-center justify-center"
          >
            <LinkIcon className="size-8 opacity-60" aria-hidden="true" />
          </div>
        )}
      </div>
      <div className="flex flex-col gap-1 p-3">
        {preview.og_site_name ? (
          <span
            data-testid="link-preview-site"
            className="text-[10px] uppercase opacity-70"
          >
            {preview.og_site_name}
          </span>
        ) : null}
        <span
          data-testid="link-preview-title"
          className="line-clamp-2 overflow-hidden text-sm font-semibold"
        >
          {title}
        </span>
        {desc ? (
          <span
            data-testid="link-preview-description"
            className="line-clamp-3 overflow-hidden text-xs opacity-80"
          >
            {desc}
          </span>
        ) : null}
        <span className="sr-only">External link: {title}</span>
      </div>
    </a>
  );
}

export default LinkPreviewCard;
