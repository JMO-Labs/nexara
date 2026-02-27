/**
 * @file tests/integration/feed.test.ts
 * @brief Integration test for the feed functionality.
 *
 * Tests the full cycle: loading posts from the API, creating a new
 * post, and verifying real-time prepend behavior.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFeedStore } from '~/stores/feed'
import type { Post, PaginatedResponse } from '~/types/api'

const mockPosts: Post[] = [
  {
    id: 'p1',
    content: 'First post in the feed',
    author: { id: 'u1', username: 'alice', display_name: 'Alice', avatar_url: null },
    media: [],
    reactions: [{ emoji: '👍', count: 2, reacted_by_me: false }],
    comment_count: 1,
    created_at: '2026-02-26T10:00:00Z',
    updated_at: '2026-02-26T10:00:00Z',
  },
  {
    id: 'p2',
    content: 'Second post',
    author: { id: 'u2', username: 'bob', display_name: 'Bob', avatar_url: null },
    media: [],
    reactions: [],
    comment_count: 0,
    created_at: '2026-02-26T09:00:00Z',
    updated_at: '2026-02-26T09:00:00Z',
  },
]

describe('feed integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('loads posts from API and appends to store', async () => {
    const store = useFeedStore()
    const response: PaginatedResponse<Post> = {
      items: mockPosts,
      cursor: 'next-cursor',
      has_more: true,
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(response), { status: 200 }),
    )

    await store.fetchPosts()

    expect(store.posts).toHaveLength(2)
    expect(store.posts[0].content).toBe('First post in the feed')
    expect(store.hasMore).toBe(true)
  })

  it('creating a post adds it to the top of the feed', async () => {
    const store = useFeedStore()

    /* Load existing posts */
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ items: mockPosts, cursor: null, has_more: false }), { status: 200 }),
    )
    await store.fetchPosts()

    /* Create a new post */
    const newPost: Post = {
      id: 'p-new',
      content: 'Just created this!',
      author: { id: 'u1', username: 'alice', display_name: 'Alice', avatar_url: null },
      media: [],
      reactions: [],
      comment_count: 0,
      created_at: '2026-02-26T11:00:00Z',
      updated_at: '2026-02-26T11:00:00Z',
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(newPost), { status: 201 }),
    )
    await store.createPost('Just created this!', [])

    expect(store.posts[0].id).toBe('p-new')
    expect(store.posts).toHaveLength(3)
  })

  it('real-time SSE post prepended without duplication', async () => {
    const store = useFeedStore()

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ items: mockPosts, cursor: null, has_more: false }), { status: 200 }),
    )
    await store.fetchPosts()

    /* Simulate SSE feed_update */
    const ssePost: Post = {
      id: 'p-sse',
      content: 'From SSE',
      author: { id: 'u3', username: 'carol', display_name: 'Carol', avatar_url: null },
      media: [],
      reactions: [],
      comment_count: 0,
      created_at: '2026-02-26T12:00:00Z',
      updated_at: '2026-02-26T12:00:00Z',
    }

    store.prependPost(ssePost)
    expect(store.posts[0].id).toBe('p-sse')
    expect(store.posts).toHaveLength(3)

    /* Duplicate SSE should not add again */
    store.prependPost(ssePost)
    expect(store.posts).toHaveLength(3)
  })

  it('optimistic reaction toggle works end-to-end', async () => {
    const store = useFeedStore()

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ items: mockPosts, cursor: null, has_more: false }), { status: 200 }),
    )
    await store.fetchPosts()

    /* Toggle reaction on */
    store.addReaction('p1', '👍')
    let reaction = store.posts[0].reactions.find(r => r.emoji === '👍')
    expect(reaction?.reacted_by_me).toBe(true)
    expect(reaction?.count).toBe(3)

    /* Toggle reaction off */
    store.addReaction('p1', '👍')
    reaction = store.posts[0].reactions.find(r => r.emoji === '👍')
    expect(reaction?.reacted_by_me).toBe(false)
    expect(reaction?.count).toBe(2)
  })
})
