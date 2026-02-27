/**
 * @file tests/components/feed/PostComposer.test.ts
 * @brief TDD tests for the PostComposer component.
 *
 * Verifies content submission, textarea behavior, and
 * submit event emission with content and media IDs.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import PostComposer from "~/components/feed/PostComposer.vue";

describe("PostComposer", () => {
  beforeEach(() => {
    /* fresh state per test */
  });

  it("renders a textarea for post content", () => {
    const wrapper = mount(PostComposer);
    const textarea = wrapper.find("textarea");

    expect(textarea.exists()).toBe(true);
  });

  it("emits submit event with content on form submission", async () => {
    const wrapper = mount(PostComposer);
    const textarea = wrapper.find("textarea");

    await textarea.setValue("My new post content");
    await wrapper.find("form").trigger("submit");

    expect(wrapper.emitted("submit")).toBeTruthy();
    expect(wrapper.emitted("submit")![0]).toEqual([
      { content: "My new post content", mediaIds: [] },
    ]);
  });

  it("clears the textarea after submission", async () => {
    const wrapper = mount(PostComposer);
    const textarea = wrapper.find("textarea");

    await textarea.setValue("Content to clear");
    await wrapper.find("form").trigger("submit");

    expect((textarea.element as HTMLTextAreaElement).value).toBe("");
  });

  it("disables submit button when content is empty", () => {
    const wrapper = mount(PostComposer);
    const button = wrapper.find('button[type="submit"]');

    expect(button.attributes("disabled")).toBeDefined();
  });

  it("enables submit button when content is non-empty", async () => {
    const wrapper = mount(PostComposer);
    const textarea = wrapper.find("textarea");

    await textarea.setValue("Some content");

    const button = wrapper.find('button[type="submit"]');
    expect(button.attributes("disabled")).toBeUndefined();
  });

  it("has accessible label on the textarea", () => {
    const wrapper = mount(PostComposer);
    const textarea = wrapper.find("textarea");

    const hasLabel =
      textarea.attributes("aria-label") || wrapper.find("label[for]").exists();

    expect(hasLabel).toBeTruthy();
  });
});
