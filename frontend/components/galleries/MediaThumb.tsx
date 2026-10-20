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
}

export function MediaThumb({
  mediaId,
  alt = "",
  zoomOnHover = false,
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

  return (
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
        display: "block",
        transition: zoomOnHover
          ? "transform 800ms cubic-bezier(0.22,1,0.36,1)"
          : undefined,
      }}
    />
  );
}

export default MediaThumb;
