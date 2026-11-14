/**
 * @file lib/api/bookmarks.ts
 * @brief Bookmark REST endpoints (toggle + cursor-paginated list).
 */
import { apiGet, apiPost, seg } from "./client";
import type { Post } from "./posts";

export interface BookmarkToggle {
  post_id: string;
  is_bookmarked: boolean;
  created_at?: string | null;
}

export interface Bookmark {
  id: string;
  post: Post;
  bookmarked_at: string;
}

export interface BookmarkPage {
  bookmarks: Bookmark[];
  pagination: { cursor: string | null; has_more: boolean };
}

/**
 * @brief Toggle a bookmark on a post.
 * @param postId post id
 * @return new bookmark state
 */
export const toggleBookmark = (postId: string) =>
  apiPost<BookmarkToggle>(`/api/v1/posts/${seg(postId)}/bookmark`);

/**
 * @brief List the viewer's bookmarks.
 * @param cursor opaque cursor or null
 * @param limit page size
 * @return page of bookmarks
 */
export const listBookmarks = (cursor: string | null = null, limit = 20) => {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (cursor) qs.set("cursor", cursor);
  return apiGet<BookmarkPage>(`/api/v1/bookmarks?${qs}`);
};
