/**
 * @file tests/components/feed/PostCard.test.ts
 * @brief TDD tests for the PostCard component.
 *
 * Verifies Markdown rendering, media thumbnail display, reaction counts,
 * author info, post navigation link, and accessibility attributes.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import PostCard from "~/components/feed/PostCard.vue";
import MediaGrid from "~/components/media/MediaGrid.vue";
import type { Post } from "~/types/api";

const basePost: Post = {
  id: "post-1",
  content: "**Bold text** and a [link](https://example.com)",
  author: {
    id: "user-1",
    username: "alice",
    display_name: "Alice Smith",
    avatar_url: null,
  },
  media: [],
  reactions: [
    { emoji: "👍", count: 5, reacted_by_me: false },
    { emoji: "❤️", count: 2, reacted_by_me: true },
  ],
  comment_count: 3,
  created_at: "2026-02-26T10:00:00Z",
  updated_at: "2026-02-26T10:00:00Z",
};

describe("PostCard", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders post content as Markdown HTML", () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });
    const content = wrapper.find('[data-testid="post-content"]');

    expect(content.html()).toContain("<strong>");
    expect(content.html()).toContain("Bold text");
  });

  it("displays the author display name", () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });

    expect(wrapper.text()).toContain("Alice Smith");
  });

  it("displays the author username", () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });

    expect(wrapper.text()).toContain("@alice");
  });

  it("shows reaction counts", () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });

    expect(wrapper.text()).toContain("👍");
    expect(wrapper.text()).toContain("5");
    expect(wrapper.text()).toContain("❤️");
    expect(wrapper.text()).toContain("2");
  });

  it("displays media thumbnails when media is present", () => {
    const postWithMedia: Post = {
      ...basePost,
      media: [
        {
          id: "media-1",
          url: "/media/photo.jpg",
          thumbnail_url: "/media/photo_thumb.webp",
          mime_type: "image/jpeg",
          width: 800,
          height: 600,
        },
      ],
    };

    const wrapper = mount(PostCard, { props: { post: postWithMedia } });
    const grid = wrapper.findComponent(MediaGrid);

    expect(grid.exists()).toBe(true);
    expect(grid.props("items")).toEqual(postWithMedia.media);
  });

  it("shows comment count", () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });

    expect(wrapper.text()).toContain("3");
  });

  it("emits react event when a reaction is clicked", async () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });
    const reactionBtn = wrapper.find('[data-testid="reaction-👍"]');

    await reactionBtn.trigger("click");

    expect(wrapper.emitted("react")).toBeTruthy();
    expect(wrapper.emitted("react")![0]).toEqual(["post-1", "👍"]);
  });

  it("has article role for accessibility", () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });

    expect(wrapper.find("article").exists()).toBe(true);
  });

  it("renders a link to the post detail page", () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });
    const link = wrapper.find('[data-testid="post-detail-link"]');

    expect(link.exists()).toBe(true);
    expect(link.attributes("to") || link.attributes("href")).toContain(
      "/app/post/post-1",
    );
  });

  it("has group class on article for hover reactions", () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });

    expect(wrapper.find("article").classes()).toContain("group");
  });

  it("does not show quick-reaction presets in display-only reaction bar", () => {
    const wrapper = mount(PostCard, { props: { post: basePost } });

    expect(wrapper.find('[data-testid="quick-reactions"]').exists()).toBe(false);
  });
});
