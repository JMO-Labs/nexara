/**
 * @file tests/components/feed/PostComposer.test.ts
 * @brief Tests for the PostComposer component.
 *
 * Verifies content submission, textarea behavior, media attachment UI,
 * image-only posts, error handling, and form reset on success.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { defineComponent } from "vue";
import { setActivePinia, createPinia } from "pinia";
import PostComposer from "~/components/feed/PostComposer.vue";

const mockCreatePost = vi.fn();

vi.mock("~/stores/feed", () => ({
  useFeedStore: () => ({
    createPost: mockCreatePost,
    posts: [],
    cursor: null,
    hasMore: true,
    loading: false,
  }),
}));

/** @brief Stub that emits upload when clicked (simulates successful upload). */
const UploadZoneStub = defineComponent({
  template:
    "<div data-testid=\"upload-stub\" @click=\"$emit('upload', { id: 'media-1' })\" />",
  emits: ["upload", "error"],
});

describe("PostComposer", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockCreatePost.mockReset();
    mockCreatePost.mockResolvedValue(undefined);
  });

  it("renders a textarea for post content", () => {
    const wrapper = mount(PostComposer);
    expect(wrapper.find("textarea").exists()).toBe(true);
  });

  it("calls feedStore.createPost with content on submission", async () => {
    const wrapper = mount(PostComposer);
    await wrapper.find("textarea").setValue("My new post content");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(mockCreatePost).toHaveBeenCalledWith(
      "My new post content",
      [],
      undefined,
    );
  });

  it("clears the textarea after successful submission", async () => {
    const wrapper = mount(PostComposer);
    const textarea = wrapper.find("textarea");

    await textarea.setValue("Content to clear");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect((textarea.element as HTMLTextAreaElement).value).toBe("");
  });

  it("preserves content when createPost fails", async () => {
    mockCreatePost.mockRejectedValue(new Error("API error"));
    const wrapper = mount(PostComposer);
    const textarea = wrapper.find("textarea");

    await textarea.setValue("Keep this content");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect((textarea.element as HTMLTextAreaElement).value).toBe(
      "Keep this content",
    );
  });

  it("disables submit button when no content and no media", () => {
    const wrapper = mount(PostComposer);
    const button = wrapper.find('button[type="submit"]');
    expect(button.attributes("disabled")).toBeDefined();
  });

  it("enables submit button when content is non-empty", async () => {
    const wrapper = mount(PostComposer);
    await wrapper.find("textarea").setValue("Some content");
    const button = wrapper.find('button[type="submit"]');
    expect(button.attributes("disabled")).toBeUndefined();
  });

  it("enables submit button for image-only posts", async () => {
    const wrapper = mount(PostComposer, {
      global: { stubs: { UploadZone: UploadZoneStub } },
    });
    // Open plus menu, click media option
    await wrapper.find('[aria-label="Attach"]').trigger("click");
    await wrapper.find('[aria-label="feed.attachMedia"]').trigger("click");
    await wrapper.find('[data-testid="upload-stub"]').trigger("click");

    const button = wrapper.find('button[type="submit"]');
    expect(button.attributes("disabled")).toBeUndefined();
  });

  it("submits image-only post with empty content", async () => {
    const wrapper = mount(PostComposer, {
      global: { stubs: { UploadZone: UploadZoneStub } },
    });
    await wrapper.find('[aria-label="Attach"]').trigger("click");
    await wrapper.find('[aria-label="feed.attachMedia"]').trigger("click");
    await wrapper.find('[data-testid="upload-stub"]').trigger("click");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(mockCreatePost).toHaveBeenCalledWith("", ["media-1"], undefined);
  });

  it("resets upload zone after successful submission", async () => {
    const wrapper = mount(PostComposer, {
      global: { stubs: { UploadZone: UploadZoneStub } },
    });
    await wrapper.find('[aria-label="Attach"]').trigger("click");
    await wrapper.find('[aria-label="feed.attachMedia"]').trigger("click");
    await wrapper.find('[data-testid="upload-stub"]').trigger("click");
    await wrapper.find("textarea").setValue("Post with media");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(wrapper.find('[data-testid="upload-stub"]').exists()).toBe(false);
  });

  it("has accessible label on the textarea", () => {
    const wrapper = mount(PostComposer);
    const textarea = wrapper.find("textarea");
    const hasLabel =
      textarea.attributes("aria-label") || wrapper.find("label[for]").exists();
    expect(hasLabel).toBeTruthy();
  });
});
