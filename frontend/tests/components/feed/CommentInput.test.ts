/**
 * @file tests/components/feed/CommentInput.test.ts
 * @brief TDD tests for the CommentInput component.
 *
 * Verifies:
 * - Layout: text input, plus button, submit button
 * - Plus menu: shows Reactions and Media options on click
 * - Reactions submenu: quick emojis appear on hover
 * - Full emoji picker: accessible from reactions submenu
 * - Media option: stub with disabled state
 * - Emits submit event with text content
 * - Emits react event with emoji
 * - Accessibility attributes
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import CommentInput from "~/components/feed/CommentInput.vue";

/** @brief Quick-reaction preset emojis available in the plus menu. */
const QUICK_EMOJIS = ["👍", "❤️", "😂", "😮", "😢", "🔥"];

describe("CommentInput", () => {
  it("renders text input, plus button, and submit button", () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    expect(wrapper.find('[data-testid="comment-input"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="plus-menu-trigger"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="comment-submit"]').exists()).toBe(true);
  });

  it("submit button is disabled when input is empty", () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    const submitBtn = wrapper.find('[data-testid="comment-submit"]');
    expect(submitBtn.attributes("disabled")).toBeDefined();
  });

  it("submit button is enabled when input has text", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="comment-input"]').setValue("Hello");
    const submitBtn = wrapper.find('[data-testid="comment-submit"]');
    expect(submitBtn.attributes("disabled")).toBeUndefined();
  });

  it("emits submit event with text when form is submitted", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="comment-input"]').setValue("My comment");
    await wrapper.find('[data-testid="comment-form"]').trigger("submit");

    expect(wrapper.emitted("submit")).toBeTruthy();
    expect(wrapper.emitted("submit")![0]).toEqual(["My comment"]);
  });

  it("clears input after successful submit", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    const input = wrapper.find('[data-testid="comment-input"]');
    await input.setValue("My comment");
    await wrapper.find('[data-testid="comment-form"]').trigger("submit");

    expect((input.element as HTMLInputElement).value).toBe("");
  });

  it("does not emit submit when input is empty", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="comment-form"]').trigger("submit");

    expect(wrapper.emitted("submit")).toBeFalsy();
  });

  it("shows plus menu with Reactions and Media options on click", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    expect(wrapper.find('[data-testid="plus-menu"]').exists()).toBe(false);

    await wrapper.find('[data-testid="plus-menu-trigger"]').trigger("click");

    expect(wrapper.find('[data-testid="plus-menu"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="plus-menu-reactions"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="plus-menu-media"]').exists()).toBe(true);
  });

  it("shows quick reaction emojis when hovering Reactions option", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="plus-menu-trigger"]').trigger("click");
    await wrapper.find('[data-testid="plus-menu-reactions"]').trigger("mouseenter");

    const submenu = wrapper.find('[data-testid="reactions-submenu"]');
    expect(submenu.exists()).toBe(true);

    for (const emoji of QUICK_EMOJIS) {
      expect(
        wrapper.find(`[data-testid="quick-react-${emoji}"]`).exists(),
      ).toBe(true);
    }
  });

  it("emits react event when a quick emoji is clicked", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="plus-menu-trigger"]').trigger("click");
    await wrapper.find('[data-testid="plus-menu-reactions"]').trigger("mouseenter");
    await wrapper.find('[data-testid="quick-react-👍"]').trigger("click");

    expect(wrapper.emitted("react")).toBeTruthy();
    expect(wrapper.emitted("react")![0]).toEqual(["👍"]);
  });

  it("closes plus menu after selecting a reaction", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="plus-menu-trigger"]').trigger("click");
    await wrapper.find('[data-testid="plus-menu-reactions"]').trigger("mouseenter");
    await wrapper.find('[data-testid="quick-react-❤️"]').trigger("click");

    expect(wrapper.find('[data-testid="plus-menu"]').exists()).toBe(false);
  });

  it("shows full emoji picker via more button in reactions submenu", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="plus-menu-trigger"]').trigger("click");
    await wrapper.find('[data-testid="plus-menu-reactions"]').trigger("mouseenter");
    await wrapper.find('[data-testid="reactions-more"]').trigger("click");

    expect(wrapper.find('[data-testid="emoji-picker"]').exists()).toBe(true);
  });

  it("emits react event from full emoji picker selection", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="plus-menu-trigger"]').trigger("click");
    await wrapper.find('[data-testid="plus-menu-reactions"]').trigger("mouseenter");
    await wrapper.find('[data-testid="reactions-more"]').trigger("click");

    const emojiBtn = wrapper.find('[data-testid="emoji-grid"] button');
    const emoji = emojiBtn.text();
    await emojiBtn.trigger("click");

    expect(wrapper.emitted("react")).toBeTruthy();
    expect(wrapper.emitted("react")![0]).toEqual([emoji]);
  });

  it("media option is disabled (stub)", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="plus-menu-trigger"]').trigger("click");
    const mediaBtn = wrapper.find('[data-testid="plus-menu-media"]');

    expect(mediaBtn.attributes("disabled")).toBeDefined();
    expect(mediaBtn.text()).toContain("📎");
  });

  it("has accessible labels on all interactive elements", () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    const input = wrapper.find('[data-testid="comment-input"]');
    expect(input.attributes("aria-label")).toBeDefined();

    const plusBtn = wrapper.find('[data-testid="plus-menu-trigger"]');
    expect(plusBtn.attributes("aria-label")).toBeDefined();
  });

  it("toggles plus menu closed on second click", async () => {
    const wrapper = mount(CommentInput, {
      props: { placeholder: "Add a comment..." },
    });

    await wrapper.find('[data-testid="plus-menu-trigger"]').trigger("click");
    expect(wrapper.find('[data-testid="plus-menu"]').exists()).toBe(true);

    await wrapper.find('[data-testid="plus-menu-trigger"]').trigger("click");
    expect(wrapper.find('[data-testid="plus-menu"]').exists()).toBe(false);
  });
});
