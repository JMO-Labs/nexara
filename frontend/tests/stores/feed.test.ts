/**
 * @file tests/stores/feed.test.ts
 * @brief TDD tests for the feed Pinia store.
 *
 * Tests fetchPosts, createPost, addReaction, and addComment actions.
 * Written before the store implementation (TDD red phase).
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useFeedStore } from "~/stores/feed";
import type { Post, PaginatedResponse } from "~/types/api";

const mockPost: Post = {
  id: "post-1",
  content: "# Hello World\nThis is a test post.",
  author: {
    id: "user-1",
    username: "alice",
    display_name: "Alice",
    avatar_url: null,
  },
  media: [],
  reactions: [{ emoji: "👍", count: 3, reacted_by_me: false }],
  comment_count: 2,
  created_at: "2026-02-26T10:00:00Z",
  updated_at: "2026-02-26T10:00:00Z",
};

const mockPost2: Post = {
  ...mockPost,
  id: "post-2",
  content: "Second post content",
  created_at: "2026-02-26T09:00:00Z",
};

const mockPaginatedResponse: PaginatedResponse<Post> = {
  items: [mockPost, mockPost2],
  cursor: "cursor-abc",
  has_more: true,
};

describe("feed store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it("starts with empty posts", () => {
    const store = useFeedStore();

    expect(store.posts).toEqual([]);
    expect(store.cursor).toBeNull();
    expect(store.hasMore).toBe(true);
    expect(store.loading).toBe(false);
  });

  it("fetchPosts() appends posts to the array", async () => {
    const store = useFeedStore();

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockPaginatedResponse), { status: 200 }),
    );

    await store.fetchPosts();

    expect(store.posts).toHaveLength(2);
    expect(store.posts[0].id).toBe("post-1");
    expect(store.posts[1].id).toBe("post-2");
    expect(store.cursor).toBe("cursor-abc");
    expect(store.hasMore).toBe(true);
  });

  it("fetchPosts() sets hasMore to false when no more pages", async () => {
    const store = useFeedStore();
    const lastPage: PaginatedResponse<Post> = {
      items: [mockPost],
      cursor: null,
      has_more: false,
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(lastPage), { status: 200 }),
    );

    await store.fetchPosts();

    expect(store.hasMore).toBe(false);
    expect(store.cursor).toBeNull();
  });

  it("createPost() prepends the new post to the array", async () => {
    const store = useFeedStore();

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockPaginatedResponse), { status: 200 }),
    );
    await store.fetchPosts();

    const newPost: Post = {
      ...mockPost,
      id: "post-new",
      content: "Brand new post",
      created_at: "2026-02-26T11:00:00Z",
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(newPost), { status: 201 }),
    );

    await store.createPost("Brand new post", []);

    expect(store.posts[0].id).toBe("post-new");
    expect(store.posts).toHaveLength(3);
  });

  it("addReaction() toggles reaction optimistically", () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost }];

    store.addReaction("post-1", "👍");

    const reaction = store.posts[0].reactions.find((r) => r.emoji === "👍");
    expect(reaction?.reacted_by_me).toBe(true);
    expect(reaction?.count).toBe(4);
  });

  it("addReaction() removes reaction when already reacted", () => {
    const store = useFeedStore();
    store.posts = [
      {
        ...mockPost,
        reactions: [{ emoji: "👍", count: 4, reacted_by_me: true }],
      },
    ];

    store.addReaction("post-1", "👍");

    const reaction = store.posts[0].reactions.find((r) => r.emoji === "👍");
    expect(reaction?.reacted_by_me).toBe(false);
    expect(reaction?.count).toBe(3);
  });

  it("addReaction() creates new emoji if not present", () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost }];

    store.addReaction("post-1", "❤️");

    const reaction = store.posts[0].reactions.find((r) => r.emoji === "❤️");
    expect(reaction).toBeDefined();
    expect(reaction?.count).toBe(1);
    expect(reaction?.reacted_by_me).toBe(true);
  });

  it("prependPost() adds a post to the top (for SSE real-time)", () => {
    const store = useFeedStore();
    store.posts = [mockPost];

    const incoming: Post = {
      ...mockPost,
      id: "post-realtime",
      content: "Real-time post via SSE",
    };

    store.prependPost(incoming);

    expect(store.posts[0].id).toBe("post-realtime");
    expect(store.posts).toHaveLength(2);
  });

  it("prependPost() does not duplicate existing post", () => {
    const store = useFeedStore();
    store.posts = [mockPost];

    store.prependPost(mockPost);

    expect(store.posts).toHaveLength(1);
  });
});
