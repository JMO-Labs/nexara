"use client";
/**
 * @file components/media/MediaCard.tsx
 * @brief Thumbnail tile with filename + size.
 */
import * as React from "react";
import { Card } from "@/components/ui";
import { API_BASE } from "@/lib/auth/session";
import type { MediaItem } from "@/lib/api/media";

export interface MediaCardProps {
  media: MediaItem;
  onSelect?: (m: MediaItem) => void;
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function MediaCard({ media, onSelect }: MediaCardProps) {
  const thumb = `${API_BASE}/api/v1/media/${media.id}/thumbnail`;
  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(media)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect?.(media);
        }
      }}
      className={`overflow-hidden outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${onSelect ? "cursor-pointer" : "cursor-default"}`}
    >
      <div
        role="img"
        className="aspect-square bg-bg bg-cover bg-center"
        style={{ backgroundImage: `url(${thumb})` }}
        aria-label={media.alt_text ?? media.filename}
      />
      <div className="flex flex-col gap-0.5 p-3">
        <p className="truncate text-sm">{media.filename}</p>
        <p className="text-xs text-muted">{fmtSize(media.size_bytes)}</p>
      </div>
    </Card>
  );
}

export default MediaCard;
