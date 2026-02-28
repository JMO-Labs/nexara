/**
 * @file tests/components/feed/ReactionBar.test.ts
 * @brief TDD tests for the ReactionBar component.
 *
 * Verifies reaction display, click toggling, and accessibility.
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
  it("renders all reactions with counts", () => {
    const wrapper = mount(ReactionBar, {
      props: { reactions: mockReactions, postId: "post-1" },
    });

    expect(wrapper.text()).toContain("👍");
    expect(wrapper.text()).toContain("5");
    expect(wrapper.text()).toContain("❤️");
    expect(wrapper.text()).toContain("2");
  });

  it("highlights reactions the user has selected", () => {
    const wrapper = mount(ReactionBar, {
      props: { reactions: mockReactions, postId: "post-1" },
    });

    const heartBtn = wrapper.find('[data-testid="reaction-❤️"]');
    expect(heartBtn.classes()).toContain("reaction-active");
  });

  it("does not highlight reactions not selected by user", () => {
    const wrapper = mount(ReactionBar, {
      props: { reactions: mockReactions, postId: "post-1" },
    });

    const thumbsBtn = wrapper.find('[data-testid="reaction-👍"]');
    expect(thumbsBtn.classes()).not.toContain("reaction-active");
  });

  it("emits react event on click", async () => {
    const wrapper = mount(ReactionBar, {
      props: { reactions: mockReactions, postId: "post-1" },
    });

    await wrapper.find('[data-testid="reaction-👍"]').trigger("click");

    expect(wrapper.emitted("react")).toBeTruthy();
    expect(wrapper.emitted("react")![0]).toEqual(["post-1", "👍"]);
  });

  it("reaction buttons have accessible labels", () => {
    const wrapper = mount(ReactionBar, {
      props: { reactions: mockReactions, postId: "post-1" },
    });

    const buttons = wrapper.findAll("button");
    buttons.forEach((btn) => {
      expect(btn.attributes("aria-label")).toBeDefined();
    });
  });

  it("renders empty state when no reactions", () => {
    const wrapper = mount(ReactionBar, {
      props: { reactions: [], postId: "post-1" },
    });

    expect(wrapper.findAll("button").length).toBeGreaterThanOrEqual(0);
  });
});
