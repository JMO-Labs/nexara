/**
 * @file tests/components/feed/CommentThread.test.ts
 * @brief TDD tests for the CommentThread component.
 *
 * Verifies rendering of nested comments, author info, reply input,
 * and comment reaction forwarding. The top-level comment input
 * lives on PostCard; CommentThread only handles replies.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import CommentThread from "~/components/feed/CommentThread.vue";
import type { Comment } from "~/types/api";

const mockComments: Comment[] = [
  {
    id: "c1",
    content: "Great post!",
    author: {
      id: "u1",
      username: "bob",
      display_name: "Bob",
      avatar_url: null,
    },
    parent_id: null,
    created_at: "2026-02-26T11:00:00Z",
    reactions: [{ emoji: "👍", count: 1, reacted_by_me: false }],
    replies: [
      {
        id: "c2",
        content: "Thanks!",
        author: {
          id: "u2",
          username: "alice",
          display_name: "Alice",
          avatar_url: null,
        },
        parent_id: "c1",
        created_at: "2026-02-26T11:05:00Z",
        reactions: [],
        replies: [],
      },
    ],
  },
  {
    id: "c3",
    content: "Interesting perspective.",
    author: {
      id: "u3",
      username: "carol",
      display_name: "Carol",
      avatar_url: null,
    },
    parent_id: null,
    created_at: "2026-02-26T12:00:00Z",
    reactions: [],
    replies: [],
  },
];

describe("CommentThread", () => {
  it("renders top-level comments", () => {
    const wrapper = mount(CommentThread, {
      props: { comments: mockComments, postId: "post-1" },
    });

    expect(wrapper.text()).toContain("Great post!");
    expect(wrapper.text()).toContain("Interesting perspective.");
  });

  it("renders nested replies", () => {
    const wrapper = mount(CommentThread, {
      props: { comments: mockComments, postId: "post-1" },
    });

    expect(wrapper.text()).toContain("Thanks!");
  });

  it("displays comment author names", () => {
    const wrapper = mount(CommentThread, {
      props: { comments: mockComments, postId: "post-1" },
    });

    expect(wrapper.text()).toContain("Bob");
    expect(wrapper.text()).toContain("Alice");
    expect(wrapper.text()).toContain("Carol");
  });

  it("emits add-comment with parentId when replying to a comment", async () => {
    const wrapper = mount(CommentThread, {
      props: { comments: mockComments, postId: "post-1" },
    });

    const replyBtn = wrapper
      .findAll("button")
      .find((b) => b.text() === "feed.reply");
    expect(replyBtn).toBeDefined();
    await replyBtn!.trigger("click");

    const replyForm = wrapper.find('[data-testid="reply-form"]');
    expect(replyForm.exists()).toBe(true);
    const replyInput = replyForm.find('[data-testid="comment-input"]');
    expect(replyInput.exists()).toBe(true);
    await replyInput.setValue("My nested reply");

    await replyForm.trigger("submit");

    expect(wrapper.emitted("add-comment")).toBeTruthy();
    expect(wrapper.emitted("add-comment")![0]).toEqual([
      { postId: "post-1", content: "My nested reply", parentId: "c1" },
    ]);
  });

  it("does not render a bottom comment form (input lives on PostCard)", () => {
    const wrapper = mount(CommentThread, {
      props: { comments: [], postId: "post-1" },
    });

    expect(wrapper.find('[data-testid="comment-form"]').exists()).toBe(false);
  });

  it("renders reaction bar on comments", () => {
    const wrapper = mount(CommentThread, {
      props: { comments: mockComments, postId: "post-1" },
    });

    const reactionBtns = wrapper.findAll('[data-testid="reaction-👍"]');
    expect(reactionBtns.length).toBeGreaterThanOrEqual(1);
  });
});
