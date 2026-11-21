/**
 * @file lib/mediaUrl.ts
 * @brief Media URL builder shared by home tiles.
 */
import { API_BASE } from "@/lib/auth/session";

/**
 * @brief URL of a media thumbnail, or the original file when none exists.
 * @param m Media with id and optional thumbnail_key.
 * @return Absolute-path URL string
 */
export function mediaThumbUrl(m: {
  id: string;
  thumbnail_key: string | null;
}): string {
  return `${API_BASE}/api/v1/media/${m.id}/${m.thumbnail_key ? "thumbnail" : "file"}`;
}
