"use client";
/**
 * @file components/galleries/MediaThumb.tsx
 * @brief Cover/thumbnail <img> with /thumbnail → /file fallback. Stretches to
 *        fill its parent (parent must establish position + size).
 */
import * as React from "react";
import { API_BASE } from "@/lib/auth/session";

export interface MediaThumbProps {
  mediaId: string | null | undefined;
  alt?: string;
  /** When true, image scales on hover via the `.nx-thumb` class. */
  zoomOnHover?: boolean;
  /** CSS object-position for cropping, e.g. "50% 30%". */
  objectPosition?: string;
  /** Cover/preview is NSFW: blur it and show a small badge (no reveal). */
  nsfw?: boolean;
}

export function MediaThumb({
  mediaId,
  alt = "",
  zoomOnHover = false,
  objectPosition,
  nsfw,
}: MediaThumbProps) {
  const [src, setSrc] = React.useState<string | null>(
    mediaId ? `${API_BASE}/api/v1/media/${mediaId}/thumbnail` : null,
  );
  const triedFile = React.useRef(false);

  React.useEffect(() => {
    triedFile.current = false;
    setSrc(mediaId ? `${API_BASE}/api/v1/media/${mediaId}/thumbnail` : null);
  }, [mediaId]);

  if (!src) return null;

  const img = (
    <img
      className={zoomOnHover ? "nx-thumb" : undefined}
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => {
        if (!triedFile.current && mediaId) {
          triedFile.current = true;
          setSrc(`${API_BASE}/api/v1/media/${mediaId}/file`);
        }
      }}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "cover",
        objectPosition,
        display: "block",
        filter: nsfw ? "blur(24px)" : undefined,
        transition: zoomOnHover
          ? "transform 800ms cubic-bezier(0.22,1,0.36,1)"
          : undefined,
      }}
    />
  );
  if (!nsfw) return img;
  return (
    <>
      {img}
      <span className="absolute top-1 left-1 rounded-full bg-[var(--nx-glass-solid)] px-1.5 py-0.5 text-[10px] font-semibold text-ink">
        NSFW
      </span>
    </>
  );
}

export default MediaThumb;
