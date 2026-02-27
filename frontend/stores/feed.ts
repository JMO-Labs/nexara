/**
 * @file stores/feed.ts
 * @brief Pinia store for the activity feed.
 *
 * Manages the list of posts with cursor-based pagination, post creation,
 * reaction toggling, and real-time prepending via SSE events.
 * Reactions use optimistic updates for a snappy UX.
 */

import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { Post, PaginatedResponse } from '~/types/api'

/** @brief API base URL for feed endpoints. */
const API_BASE = '/api/v1'

export const useFeedStore = defineStore('feed', () => {
  /** @brief Ordered list of posts in the feed. */
  const posts = ref<Post[]>([])

  /** @brief Cursor for the next page of results. */
  const cursor = ref<string | null>(null)

  /** @brief Whether more pages are available. */
  const hasMore = ref(true)

  /** @brief Whether a fetch operation is in progress. */
  const loading = ref(false)

  /**
   * @brief Fetch the next page of posts from the API.
   *
   * Appends results to the existing posts array for infinite scroll.
   */
  async function fetchPosts(): Promise<void> {
    if (loading.value) return

    loading.value = true
    try {
      const params = new URLSearchParams()
      if (cursor.value) params.set('cursor', cursor.value)

      const response = await fetch(`${API_BASE}/posts?${params}`, {
        credentials: 'include',
      })

      if (!response.ok) throw new Error('Failed to fetch posts')

      const data: PaginatedResponse<Post> = await response.json()
      posts.value.push(...data.items)
      cursor.value = data.cursor
      hasMore.value = data.has_more
    } finally {
      loading.value = false
    }
  }

  /**
   * @brief Create a new post and prepend it to the feed.
   * @param content - Markdown content of the post.
   * @param mediaIds - IDs of attached media files.
   */
  async function createPost(content: string, mediaIds: string[]): Promise<void> {
    const response = await fetch(`${API_BASE}/posts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ content, media_ids: mediaIds }),
    })

    if (!response.ok) throw new Error('Failed to create post')

    const newPost: Post = await response.json()
    posts.value.unshift(newPost)
  }

  /**
   * @brief Toggle a reaction on a post (optimistic update).
   * @param postId - ID of the post to react to.
   * @param emoji - Emoji to toggle.
   */
  function addReaction(postId: string, emoji: string): void {
    const post = posts.value.find(p => p.id === postId)
    if (!post) return

    const existing = post.reactions.find(r => r.emoji === emoji)
    if (existing) {
      if (existing.reacted_by_me) {
        existing.count--
        existing.reacted_by_me = false
      } else {
        existing.count++
        existing.reacted_by_me = true
      }
    } else {
      post.reactions.push({ emoji, count: 1, reacted_by_me: true })
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
    if (posts.value.some(p => p.id === post.id)) return
    posts.value.unshift(post)
  }

  return {
    posts,
    cursor,
    hasMore,
    loading,
    fetchPosts,
    createPost,
    addReaction,
    prependPost,
  }
})
