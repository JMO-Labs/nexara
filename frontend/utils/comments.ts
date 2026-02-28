/**
 * @file utils/comments.ts
 * @brief Utility for building nested comment trees from flat API responses.
 *
 * The backend returns comments as a flat list sorted by created_at DESC,
 * with `parent_id` set on replies. This module groups child comments
 * under their parent's `replies` array for threaded display.
 */

import type { Comment } from "~/types/api";

/**
 * @brief Build a nested comment tree from a flat comment list.
 *
 * Groups comments with a `parent_id` under their parent's `replies`
 * array. Comments whose parent is not present in the list are treated
 * as top-level. Preserves the original array order within each level.
 *
 * @param flat Flat array of comments (may include both parents and replies).
 * @returns Array of top-level comments with replies nested inside.
 */
export function buildCommentTree(flat: Comment[]): Comment[] {
  const map = new Map<string, Comment>();
  const roots: Comment[] = [];

  for (const c of flat) {
    map.set(c.id, { ...c, replies: [] });
  }

  for (const c of flat) {
    const node = map.get(c.id)!;
    if (c.parent_id && map.has(c.parent_id)) {
      map.get(c.parent_id)!.replies!.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}
