"use client";
/**
 * @file hooks/useNsfw.ts
 * @brief Gallery/media NSFW mutations (moderator + uploader), silent toasts.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { setGalleryNsfw } from "@/lib/api/moderation";
import { setMediaNsfw } from "@/lib/api/media";
import { qk } from "@/lib/query-keys";

/** @brief Moderator toggle of a gallery's NSFW flag. */
export function useSetGalleryNsfw() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, value }: { id: string; value: boolean }) =>
      setGalleryNsfw(id, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.galleries.all() }),
  });
}

/** @brief Uploader toggle of one media item's NSFW flag. */
export function useSetMediaNsfw() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, value }: { id: string; value: boolean }) =>
      setMediaNsfw(id, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.galleries.all() }),
  });
}
