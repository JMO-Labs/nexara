/**
 * @file lib/photoTitle.ts
 * @brief Display title for an aggregated home-media item.
 */
import type { HomeMediaItem } from "@/lib/api/home";

/**
 * @brief Source title, falling back to "Your uploads" for standalone uploads.
 * @param it home media item
 * @return title or null
 */
export function photoTitle(
  it: Pick<HomeMediaItem, "source" | "source_title">,
): string | null {
  return it.source_title ?? (it.source === "upload" ? "Your uploads" : null);
}
