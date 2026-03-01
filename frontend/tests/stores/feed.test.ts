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

vi.mock("~/composables/useEventBus", () => ({
  useEventBus: () => ({
    on: vi.fn(() => vi.fn()),
    off: vi.fn(),
    dispatch: vi.fn(),
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

  it("addCommentReaction() calls API and updates comment state", async () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost }];
    store.commentsByPost["post-1"] = {
      items: [
        {
          id: "comment-1",
          content: "Nice!",
          author: { id: "user-2", username: "bob", display_name: "Bob", avatar_url: null },
          parent_id: null,
          created_at: "2026-02-26T10:00:00Z",
          reactions: [],
        },
      ],
      cursor: null,
      hasMore: false,
    };

    mockPostFn.mockResolvedValueOnce({
      action: "added",
      emoji: "👍",
      count: 1,
    });

    await store.addCommentReaction("post-1", "comment-1", "👍");

    expect(mockPostFn).toHaveBeenCalledWith(
      "/posts/post-1/comments/comment-1/reactions",
      { emoji: "👍" },
    );
    const comment = store.commentsByPost["post-1"].items[0];
    const reaction = comment.reactions.find((r) => r.emoji === "👍");
    expect(reaction?.reacted_by_me).toBe(true);
    expect(reaction?.count).toBe(1);
  });

  it("addReaction() removes reaction entry when count drops to 0", async () => {
    const store = useFeedStore();
    store.posts = [
      {
        ...mockPost,
        reactions: [{ emoji: "👍", count: 1, reacted_by_me: true }],
      },
    ];

    mockPostFn.mockResolvedValueOnce({
      action: "removed",
      emoji: "👍",
      count: 0,
    });

    await store.addReaction("post-1", "👍");

    expect(store.posts[0].reactions.find((r) => r.emoji === "👍")).toBeUndefined();
  });

  it("applyReactionUpdate() updates post reactions from SSE", () => {
    const store = useFeedStore();
    store.posts = [
      {
        ...mockPost,
        reactions: [{ emoji: "👍", count: 3, reacted_by_me: false }],
      },
    ];

    store.applyReactionUpdate({
      post_id: "post-1",
      target_type: "post",
      target_id: "post-1",
      emoji: "👍",
      count: 4,
      action: "added",
      user_id: "other-user",
    });

    const reaction = store.posts[0].reactions.find((r) => r.emoji === "👍");
    expect(reaction?.count).toBe(4);
  });

  it("applyReactionUpdate() reconciles own reaction with server count (no skip)", () => {
    const store = useFeedStore();
    store.posts = [
      {
        ...mockPost,
        reactions: [{ emoji: "👍", count: 3, reacted_by_me: true }],
      },
    ];

    store.applyReactionUpdate({
      post_id: "post-1",
      target_type: "post",
      target_id: "post-1",
      emoji: "👍",
      count: 4,
      action: "added",
      user_id: "current-user",
    });

    const reaction = store.posts[0].reactions.find((r) => r.emoji === "👍");
    expect(reaction?.count).toBe(4);
    expect(reaction?.reacted_by_me).toBe(true);
  });

  it("applyReactionUpdate() removes reaction when count reaches 0", () => {
    const store = useFeedStore();
    store.posts = [
      {
        ...mockPost,
        reactions: [{ emoji: "👍", count: 1, reacted_by_me: false }],
      },
    ];

    store.applyReactionUpdate({
      post_id: "post-1",
      target_type: "post",
      target_id: "post-1",
      emoji: "👍",
      count: 0,
      action: "removed",
      user_id: "other-user",
    });

    expect(store.posts[0].reactions.find((r) => r.emoji === "👍")).toBeUndefined();
  });

  it("applyCommentUpdate() adds top-level comment from SSE", () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost, comment_count: 2 }];
    store.commentsByPost["post-1"] = { items: [], cursor: null, hasMore: false };

    store.applyCommentUpdate({
      post_id: "post-1",
      comment: {
        id: "c-new",
        content: "hello",
        author: { id: "user-2", username: "bob", display_name: "Bob", avatar_url: null },
        parent_id: null,
        created_at: "2026-02-28T10:00:00Z",
        reactions: [],
      },
    });

    expect(store.commentsByPost["post-1"].items).toHaveLength(1);
    expect(store.commentsByPost["post-1"].items[0].id).toBe("c-new");
    expect(store.posts[0].comment_count).toBe(3);
  });

  it("applyCommentUpdate() deduplicates own comment by ID (no user_id skip)", () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost, comment_count: 3 }];
    const ownComment = {
      id: "c-self",
      content: "my own",
      author: { id: "user-1", username: "alice", display_name: "Alice", avatar_url: null },
      parent_id: null,
      created_at: "2026-02-28T10:00:00Z",
      reactions: [],
    };
    store.commentsByPost["post-1"] = { items: [ownComment], cursor: null, hasMore: false };

    store.applyCommentUpdate({
      post_id: "post-1",
      comment: ownComment,
    });

    expect(store.commentsByPost["post-1"].items).toHaveLength(1);
    expect(store.posts[0].comment_count).toBe(3);
  });

  it("applyCommentUpdate() adds reply to flat items for buildCommentTree nesting", () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost }];
    store.commentsByPost["post-1"] = {
      items: [
        {
          id: "c-parent",
          content: "parent",
          author: { id: "user-1", username: "alice", display_name: "Alice", avatar_url: null },
          parent_id: null,
          created_at: "2026-02-28T10:00:00Z",
          reactions: [],
          replies: [],
        },
      ],
      cursor: null,
      hasMore: false,
    };

    store.applyCommentUpdate({
      post_id: "post-1",
      comment: {
        id: "c-reply",
        content: "reply",
        author: { id: "user-2", username: "bob", display_name: "Bob", avatar_url: null },
        parent_id: "c-parent",
        created_at: "2026-02-28T10:01:00Z",
        reactions: [],
      },
    });

    const items = store.commentsByPost["post-1"].items;
    expect(items).toHaveLength(2);
    expect(items[0].id).toBe("c-reply");
    expect(items[0].parent_id).toBe("c-parent");
  });

  it("applyCommentUpdate() deduplicates by comment ID", () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost, comment_count: 2 }];
    const existingComment = {
      id: "c-dup",
      content: "exists",
      author: { id: "user-2", username: "bob", display_name: "Bob", avatar_url: null },
      parent_id: null,
      created_at: "2026-02-28T10:00:00Z",
      reactions: [],
    };
    store.commentsByPost["post-1"] = { items: [existingComment], cursor: null, hasMore: false };

    store.applyCommentUpdate({ post_id: "post-1", comment: existingComment });

    expect(store.commentsByPost["post-1"].items).toHaveLength(1);
  });

  it("addCommentReaction() rolls back on API failure", async () => {
    const store = useFeedStore();
    store.commentsByPost["post-1"] = {
      items: [
        {
          id: "comment-1",
          content: "Nice!",
          author: { id: "user-2", username: "bob", display_name: "Bob", avatar_url: null },
          parent_id: null,
          created_at: "2026-02-26T10:00:00Z",
          reactions: [{ emoji: "👍", count: 2, reacted_by_me: false }],
        },
      ],
      cursor: null,
      hasMore: false,
    };

    mockPostFn.mockRejectedValueOnce(new Error("Network error"));

    await store.addCommentReaction("post-1", "comment-1", "👍");

    const comment = store.commentsByPost["post-1"].items[0];
    const reaction = comment.reactions.find((r) => r.emoji === "👍");
    expect(reaction?.reacted_by_me).toBe(false);
    expect(reaction?.count).toBe(2);
  });

  it("applyCommentUpdate() auto-initialises commentsByPost entry", () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost, comment_count: 0 }];

    expect(store.commentsByPost["post-1"]).toBeUndefined();

    store.applyCommentUpdate({
      post_id: "post-1",
      comment: {
        id: "c-auto",
        content: "first SSE comment",
        author: { id: "user-2", username: "bob", display_name: "Bob", avatar_url: null },
        parent_id: null,
        created_at: "2026-02-28T12:00:00Z",
        reactions: [],
      },
    });

    expect(store.commentsByPost["post-1"]).toBeDefined();
    expect(store.commentsByPost["post-1"].items).toHaveLength(1);
    expect(store.commentsByPost["post-1"].items[0].id).toBe("c-auto");
    expect(store.posts[0].comment_count).toBe(1);
  });

  it("upsertPost() adds a new post to the list", () => {
    const store = useFeedStore();
    store.posts = [mockPost];

    const incoming: Post = { ...mockPost, id: "post-new", content: "fresh" };
    store.upsertPost(incoming);

    expect(store.posts).toHaveLength(2);
    expect(store.posts[0].id).toBe("post-new");
  });

  it("upsertPost() replaces an existing post in-place", () => {
    const store = useFeedStore();
    store.posts = [mockPost, mockPost2];

    const updated: Post = { ...mockPost, content: "updated content" };
    store.upsertPost(updated);

    expect(store.posts).toHaveLength(2);
    expect(store.posts[0].content).toBe("updated content");
  });

  it("applyReactionUpdate() updates comment reactions from SSE", () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost }];
    store.commentsByPost["post-1"] = {
      items: [
        {
          id: "comment-1",
          content: "Nice!",
          author: { id: "user-2", username: "bob", display_name: "Bob", avatar_url: null },
          parent_id: null,
          created_at: "2026-02-26T10:00:00Z",
          reactions: [{ emoji: "❤️", count: 1, reacted_by_me: false }],
        },
      ],
      cursor: null,
      hasMore: false,
    };

    store.applyReactionUpdate({
      post_id: "post-1",
      target_type: "comment",
      target_id: "comment-1",
      emoji: "❤️",
      count: 2,
      action: "added",
      user_id: "other-user",
    });

    const reaction = store.commentsByPost["post-1"].items[0].reactions.find(
      (r) => r.emoji === "❤️",
    );
    expect(reaction?.count).toBe(2);
  });

  it("applyReactionUpdate() adds new emoji to post from SSE", () => {
    const store = useFeedStore();
    store.posts = [{ ...mockPost, reactions: [] }];

    store.applyReactionUpdate({
      post_id: "post-1",
      target_type: "post",
      target_id: "post-1",
      emoji: "🎉",
      count: 1,
      action: "added",
      user_id: "other-user",
    });

    const reaction = store.posts[0].reactions.find((r) => r.emoji === "🎉");
    expect(reaction).toBeDefined();
    expect(reaction?.count).toBe(1);
    expect(reaction?.reacted_by_me).toBe(false);
  });

  describe("handleFeedEvent()", () => {
    it("routes 'created' events to prependPost", () => {
      const store = useFeedStore();
      store.posts = [];

      store.handleFeedEvent({
        event: "created",
        post: { ...mockPost, id: "post-sse" },
      });

      expect(store.posts).toHaveLength(1);
      expect(store.posts[0].id).toBe("post-sse");
    });

    it("routes 'comment_created' events to applyCommentUpdate", () => {
      const store = useFeedStore();
      store.posts = [{ ...mockPost, comment_count: 0 }];

      store.handleFeedEvent({
        event: "comment_created",
        post_id: "post-1",
        comment: {
          id: "c-live",
          content: "live comment",
          author: { id: "user-2", username: "bob", display_name: "Bob", avatar_url: null },
          parent_id: null,
          created_at: "2026-02-28T10:00:00Z",
          reactions: [],
        },
      });

      expect(store.commentsByPost["post-1"].items).toHaveLength(1);
      expect(store.posts[0].comment_count).toBe(1);
    });

    it("routes 'reaction_toggled' events to applyReactionUpdate", () => {
      const store = useFeedStore();
      store.posts = [{ ...mockPost, reactions: [{ emoji: "👍", count: 1, reacted_by_me: false }] }];

      store.handleFeedEvent({
        event: "reaction_toggled",
        post_id: "post-1",
        target_type: "post",
        target_id: "post-1",
        emoji: "👍",
        count: 2,
        action: "added",
        user_id: "other-user",
      });

      expect(store.posts[0].reactions[0].count).toBe(2);
    });

    it("ignores unknown event types without error", () => {
      const store = useFeedStore();
      store.posts = [mockPost];

      expect(() => store.handleFeedEvent({ event: "unknown" })).not.toThrow();
      expect(store.posts).toHaveLength(1);
    });
  });
});
