"use client";
/**
 * @file components/galleries/GalleryCard.tsx
 * @brief Gallery tile with cover thumbnail + metadata + owner avatar.
 */
import * as React from "react";
import { Card, Badge, Avatar } from "@/components/ui";
import { API_BASE } from "@/lib/auth/session";
import { MediaThumb } from "./MediaThumb";
import type { Gallery } from "@/lib/api/galleries";

export interface GalleryCardProps {
  gallery: Gallery;
  onSelect: (id: string) => void;
}

/**
 * @brief Clickable gallery tile.
 * @param gallery gallery to show
 * @param onSelect called with the gallery id on click / Enter / Space
 * @return card element
 */
export function GalleryCard({ gallery, onSelect }: GalleryCardProps) {
  return (
    <Card
      role="button"
      tabIndex={0}
      aria-label={gallery.title}
      onClick={() => onSelect(gallery.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(gallery.id);
        }
      }}
      className="cursor-pointer overflow-hidden outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      <div className="bg-bg relative aspect-[4/3] overflow-hidden">
        <MediaThumb
          mediaId={gallery.cover_media_id}
          alt={`${gallery.title} cover`}
        />
        <div className="absolute inset-x-0 bottom-0 flex items-center gap-2 bg-gradient-to-t from-black/60 to-transparent px-2 pt-4 pb-2">
          <span data-testid="gallery-card-owner-avatar">
            <Avatar
              size="sm"
              src={`${API_BASE}/api/v1/users/${gallery.owner_id}/avatar`}
              name={gallery.owner_id}
            />
          </span>
          <span className="flex-1 truncate text-xs font-semibold text-white">
            {gallery.owner_id}
          </span>
        </div>
      </div>
      <div className="flex flex-col gap-1 p-4">
        <h3 className="truncate text-base font-semibold">{gallery.title}</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-ink/70">
            {gallery.item_count} {gallery.item_count === 1 ? "item" : "items"}
          </span>
          {gallery.is_featured && <Badge tone="sun">Featured</Badge>}
        </div>
      </div>
    </Card>
  );
}

export default GalleryCard;
