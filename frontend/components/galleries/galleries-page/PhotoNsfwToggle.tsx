"use client";
/**
 * @file components/galleries/galleries-page/PhotoNsfwToggle.tsx
 * @brief Uploader's per-photo NSFW toggle: shows and flips only the photo's own
 *        flag; disabled when a moderator/container lock applies.
 */
import { IconButton } from "@/components/ui";
import { useSetMediaNsfw } from "@/hooks/useNsfw";
import type { GalleryItem } from "@/lib/api/galleries";

/** @param item gallery item carrying own flag and effective lock */
export function PhotoNsfwToggle({ item }: { item: GalleryItem }) {
  const mut = useSetMediaNsfw();
  const own = !!item.is_nsfw_own;
  const locked = !!item.nsfw_locked;
  const label = locked
    ? "A moderator marked this NSFW."
    : own
      ? "Remove NSFW from photo"
      : "Mark photo NSFW";
  return (
    <IconButton
      size="sm"
      variant="glass"
      aria-label={label}
      title={label}
      aria-pressed={own}
      disabled={locked}
      onClick={() => mut.mutate({ id: item.media_id, value: !own })}
      className="absolute top-1.5 left-1.5 text-xs font-bold"
    >
      NSFW
    </IconButton>
  );
}
