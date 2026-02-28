/**
 * @file stores/feed.ts
 * @brief Pinia store for the activity feed.
 *
 * Manages the list of posts with cursor-based pagination, post creation,
 * reaction toggling, and real-time prepending via SSE events.
 * Reactions use optimistic updates for a snappy UX.
 */

import { ref, reactive } from "vue";
import { defineStore } from "pinia";
import { useApi } from "~/composables/useApi";
import type { Post, Comment, PaginatedResponse } from "~/types/api";

export const useFeedStore = defineStore("feed", () => {
  /** @brief Ordered list of posts in the feed. */
  const posts = ref<Post[]>([]);

  /** @brief Cursor for the next page of results. */
  const cursor = ref<string | null>(null);

  /** @brief Whether more pages are available. */
  const hasMore = ref(true);

  /** @brief Whether a fetch operation is in progress. */
  const loading = ref(false);

  /**
   * @brief Fetch the next page of posts from the API.
   *
   * Appends results to the existing posts array for infinite scroll.
   */
  async function fetchPosts(): Promise<void> {
    if (loading.value) return;

    loading.value = true;
    try {
      const api = useApi();
      const params = new URLSearchParams();
      if (cursor.value) params.set("cursor", cursor.value);

      const data = await api.get<PaginatedResponse<Post>>(`/posts?${params}`);
      posts.value.push(...data.items);
      cursor.value = data.cursor;
      hasMore.value = data.has_more;
    } finally {
      loading.value = false;
    }
  }

  /**
   * @brief Create a new post and prepend it to the feed.
   * @param content - Markdown content of the post.
   * @param mediaIds - IDs of attached media files.
   */
  async function createPost(
    content: string,
    mediaIds: string[],
  ): Promise<void> {
    const api = useApi();
    const newPost = await api.post<Post>("/posts", {
      content,
      media_ids: mediaIds,
    });
    posts.value.unshift(newPost);
  }

  /**
   * @brief Toggle a reaction on a post with optimistic update and API call.
   *
   * Applies an immediate UI update, then sends the request to the server.
   * On failure the optimistic change is rolled back to the prior state.
   *
   * @param postId - ID of the post to react to.
   * @param emoji - Emoji to toggle.
   */
  async function addReaction(postId: string, emoji: string): Promise<void> {
    const post = posts.value.find((p) => p.id === postId);
    if (!post) return;

    const existing = post.reactions.find((r) => r.emoji === emoji);
    const snapshot = existing
      ? { count: existing.count, reacted_by_me: existing.reacted_by_me }
      : null;

    if (existing) {
      existing.reacted_by_me = !existing.reacted_by_me;
      existing.count += existing.reacted_by_me ? 1 : -1;
    } else {
      post.reactions.push({ emoji, count: 1, reacted_by_me: true });
    }

    try {
      const api = useApi();
      const result = await api.post<{
        action: string;
        emoji: string;
        count: number;
      }>(`/posts/${postId}/reactions`, { emoji });

      if (existing) {
        existing.count = result.count;
        existing.reacted_by_me = result.action === "added";
      } else {
        const added = post.reactions.find((r) => r.emoji === emoji);
        if (added) {
          added.count = result.count;
          added.reacted_by_me = result.action === "added";
        }
      }
    } catch {
      if (existing && snapshot) {
        existing.count = snapshot.count;
        existing.reacted_by_me = snapshot.reacted_by_me;
      } else {
        post.reactions = post.reactions.filter((r) => r.emoji !== emoji);
      }
    }
  }

  /**
   * @brief Edit a post's content and update it in the local list.
   * @param postId - ID of the post to edit.
   * @param content - New markdown content.
   */
  async function editPost(postId: string, content: string): Promise<void> {
    const api = useApi();
    const updated = await api.put<Post>(`/posts/${postId}`, { content });
    const idx = posts.value.findIndex((p) => p.id === postId);
    if (idx !== -1) {
      posts.value[idx] = updated;
    }
  }

  /**
   * @brief Delete a post and remove it from the local list.
   * @param postId - ID of the post to delete.
   */
  async function deletePost(postId: string): Promise<void> {
    const api = useApi();
    await api.del(`/posts/${postId}`);
    posts.value = posts.value.filter((p) => p.id !== postId);
  }

  /**
   * @brief Paginated comment state keyed by post ID.
   *
   * Each entry tracks loaded items (newest first), the next
   * pagination cursor, and whether more pages exist.
   */
  const commentsByPost = reactive<
    Record<string, { items: Comment[]; cursor: string | null; hasMore: boolean }>
  >({});

  /**
   * @brief Fetch comments for a post with cursor pagination.
   *
   * @param postId - ID of the post.
   * @param reset  - When true, discards cached comments and fetches from scratch.
   * @param limit  - Number of comments per page (default 20).
   */
  async function fetchComments(
    postId: string,
    reset = false,
    limit = 20,
  ): Promise<void> {
    const api = useApi();
    const entry = commentsByPost[postId];
    if (entry && !reset && !entry.hasMore) return;

    const params = new URLSearchParams();
    params.set("limit", String(limit));
    if (!reset && entry?.cursor) {
      params.set("cursor", entry.cursor);
    }

    const data = await api.get<{
      items: Comment[];
      cursor: string | null;
      has_more: boolean;
    }>(`/posts/${postId}/comments?${params}`);

    if (reset || !entry) {
      commentsByPost[postId] = {
        items: data.items,
        cursor: data.cursor,
        hasMore: data.has_more,
      };
    } else {
      entry.items.push(...data.items);
      entry.cursor = data.cursor;
      entry.hasMore = data.has_more;
    }
  }

  /**
   * @brief Add a comment to a post and update local state.
   *
   * New comments are prepended (newest first) to match the sort order.
   *
   * @param postId   - ID of the post.
   * @param content  - Comment text.
   * @param parentId - Optional parent comment ID for replies.
   */
  async function addComment(
    postId: string,
    content: string,
    parentId: string | null = null,
  ): Promise<void> {
    const api = useApi();
    const comment = await api.post<Comment>(`/posts/${postId}/comments`, {
      content,
      parent_id: parentId,
    });

    if (!commentsByPost[postId]) {
      commentsByPost[postId] = { items: [], cursor: null, hasMore: false };
    }
    commentsByPost[postId].items.unshift(comment);

    const post = posts.value.find((p) => p.id === postId);
    if (post) {
      post.comment_count++;
    }
  }

  /**
   * @brief Prepend a post for real-time SSE updates.
   *
   * Deduplicates by post ID to prevent double-insertion when the
   * user creates a post and also receives it via SSE.
   * @param post - The post to prepend.
   */
  function prependPost(post: Post): void {
    if (posts.value.some((p) => p.id === post.id)) return;
    posts.value.unshift(post);
  }

  return {
    posts,
    cursor,
    hasMore,
    loading,
    fetchPosts,
    createPost,
    editPost,
    deletePost,
    addReaction,
    commentsByPost,
    fetchComments,
    addComment,
    prependPost,
  };
});
