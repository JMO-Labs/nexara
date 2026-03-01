/**
 * @file tests/components/feed/ReactionBar.test.ts
 * @brief TDD tests for the display-only ReactionBar component.
 *
 * Verifies:
 * - Existing reaction display with counts
 * - Highlights user's own reactions
 * - Emits toggle event on badge click
 * - Accessibility attributes
 * - No quick-react presets or picker (display-only)
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ReactionBar from "~/components/feed/ReactionBar.vue";
import type { Reaction } from "~/types/api";

const mockReactions: Reaction[] = [
  { emoji: "👍", count: 5, reacted_by_me: false },
  { emoji: "❤️", count: 2, reacted_by_me: true },
];

describe("ReactionBar", () => {
  it("renders existing reactions with counts", () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: mockReactions,
        targetType: "post",
        targetId: "post-1",
      },
    });

    expect(wrapper.text()).toContain("👍");
    expect(wrapper.text()).toContain("5");
    expect(wrapper.text()).toContain("❤️");
    expect(wrapper.text()).toContain("2");
  });

  it("highlights reactions the user has selected", () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: mockReactions,
        targetType: "post",
        targetId: "post-1",
      },
    });

    const heartBtn = wrapper.find('[data-testid="reaction-❤️"]');
    expect(heartBtn.classes()).toContain("reaction-active");
  });

  it("does not highlight reactions not selected by user", () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: mockReactions,
        targetType: "post",
        targetId: "post-1",
      },
    });

    const thumbsBtn = wrapper.find('[data-testid="reaction-👍"]');
    expect(thumbsBtn.classes()).not.toContain("reaction-active");
  });

  it("emits react event with targetType and targetId on badge click", async () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: mockReactions,
        targetType: "post",
        targetId: "post-1",
      },
    });

    await wrapper.find('[data-testid="reaction-👍"]').trigger("click");

    expect(wrapper.emitted("react")).toBeTruthy();
    expect(wrapper.emitted("react")![0]).toEqual(["post", "post-1", "👍"]);
  });

  it("renders nothing when reactions array is empty", () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: [],
        targetType: "post",
        targetId: "post-1",
      },
    });

    expect(wrapper.findAll("button")).toHaveLength(0);
  });

  it("does not render quick-react presets", () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: mockReactions,
        targetType: "post",
        targetId: "post-1",
      },
    });

    expect(wrapper.find('[data-testid="quick-reactions"]').exists()).toBe(false);
  });

  it("does not render emoji picker toggle", () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: mockReactions,
        targetType: "post",
        targetId: "post-1",
      },
    });

    expect(wrapper.find('[data-testid="emoji-picker-toggle"]').exists()).toBe(false);
  });

  it("reaction badges have accessible labels", () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: mockReactions,
        targetType: "post",
        targetId: "post-1",
      },
    });

    const buttons = wrapper.findAll("button");
    buttons.forEach((btn) => {
      expect(btn.attributes("aria-label")).toBeDefined();
    });
  });

  it("supports comment targetType", async () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: [{ emoji: "😂", count: 1, reacted_by_me: false }],
        targetType: "comment",
        targetId: "comment-42",
      },
    });

    await wrapper.find('[data-testid="reaction-😂"]').trigger("click");

    expect(wrapper.emitted("react")![0]).toEqual(["comment", "comment-42", "😂"]);
  });

  it("supports media targetType", async () => {
    const wrapper = mount(ReactionBar, {
      props: {
        reactions: [{ emoji: "🔥", count: 3, reacted_by_me: true }],
        targetType: "media",
        targetId: "media-7",
      },
    });

    await wrapper.find('[data-testid="reaction-🔥"]').trigger("click");

    expect(wrapper.emitted("react")![0]).toEqual(["media", "media-7", "🔥"]);
  });
});
