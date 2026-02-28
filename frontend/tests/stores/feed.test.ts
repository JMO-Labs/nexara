/**
 * @file tests/stores/feed.test.ts
 * @brief TDD tests for the feed Pinia store.
 *
 * Tests fetchPosts, createPost, addReaction, and prependPost actions.
 * Mocks useApi() for HTTP calls.
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

const mockGet = vi.fn();
const mockPostFn = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: mockGet,
    post: mockPostFn,
    put: vi.fn(),
    del: vi.fn(),
  }),
}));

describe("feed store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
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
    mockGet.mockResolvedValueOnce(mockPaginatedResponse);

    await store.fetchPosts();

    expect(mockGet).toHaveBeenCalledWith("/posts?");
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
    mockGet.mockResolvedValueOnce(lastPage);

    await store.fetchPosts();

    expect(store.hasMore).toBe(false);
    expect(store.cursor).toBeNull();
  });

  it("createPost() prepends the new post to the array", async () => {
    const store = useFeedStore();
    mockGet.mockResolvedValueOnce(mockPaginatedResponse);
    await store.fetchPosts();

    const newPost: Post = {
      ...mockPost,
      id: "post-new",
      content: "Brand new post",
      created_at: "2026-02-26T11:00:00Z",
    };
    mockPostFn.mockResolvedValueOnce(newPost);

    await store.createPost("Brand new post", []);

    expect(mockPostFn).toHaveBeenCalledWith("/posts", {
      content: "Brand new post",
      media_ids: [],
    });
    expect(store.posts[0].id).toBe("post-new");
    expect(store.posts).toHaveLength(3);
  });

  it("addReaction() calls API and updates state on success", async () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost }];

    mockPostFn.mockResolvedValueOnce({
      action: "added",
      emoji: "👍",
      count: 4,
    });

    await store.addReaction("post-1", "👍");

    expect(mockPostFn).toHaveBeenCalledWith("/posts/post-1/reactions", {
      emoji: "👍",
    });
    const reaction = store.posts[0].reactions.find((r) => r.emoji === "👍");
    expect(reaction?.reacted_by_me).toBe(true);
    expect(reaction?.count).toBe(4);
  });

  it("addReaction() removes reaction via API when already reacted", async () => {
    const store = useFeedStore();
    store.posts = [
      {
        ...mockPost,
        reactions: [{ emoji: "👍", count: 4, reacted_by_me: true }],
      },
    ];

    mockPostFn.mockResolvedValueOnce({
      action: "removed",
      emoji: "👍",
      count: 3,
    });

    await store.addReaction("post-1", "👍");

    expect(mockPostFn).toHaveBeenCalledWith("/posts/post-1/reactions", {
      emoji: "👍",
    });
    const reaction = store.posts[0].reactions.find((r) => r.emoji === "👍");
    expect(reaction?.reacted_by_me).toBe(false);
    expect(reaction?.count).toBe(3);
  });

  it("addReaction() creates new emoji if not present", async () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost }];

    mockPostFn.mockResolvedValueOnce({
      action: "added",
      emoji: "❤️",
      count: 1,
    });

    await store.addReaction("post-1", "❤️");

    const reaction = store.posts[0].reactions.find((r) => r.emoji === "❤️");
    expect(reaction).toBeDefined();
    expect(reaction?.count).toBe(1);
    expect(reaction?.reacted_by_me).toBe(true);
  });

  it("addReaction() rolls back on API failure", async () => {
    const store = useFeedStore();
    store.posts = [
      {
        ...mockPost,
        reactions: [{ emoji: "👍", count: 3, reacted_by_me: false }],
      },
    ];

    mockPostFn.mockRejectedValueOnce(new Error("Network error"));

    await store.addReaction("post-1", "👍");

    const reaction = store.posts[0].reactions.find((r) => r.emoji === "👍");
    expect(reaction?.reacted_by_me).toBe(false);
    expect(reaction?.count).toBe(3);
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
