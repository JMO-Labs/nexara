/**
 * @file tests/components/content/VideoEmbed.test.ts
 * @brief TDD tests for the VideoEmbed component.
 *
 * Verifies play button display, iframe after click, and provider URLs.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import VideoEmbed from "~/components/content/VideoEmbed.vue";

describe("VideoEmbed", () => {
  it("renders play button initially", () => {
    const wrapper = mount(VideoEmbed, {
      props: { providerType: "youtube", providerId: "dQw4w9WgXcQ" },
    });
    expect(wrapper.find("[data-testid=\"play-button\"]").exists()).toBe(true);
  });

  it("shows iframe after click", async () => {
    const wrapper = mount(VideoEmbed, {
      props: { providerType: "youtube", providerId: "dQw4w9WgXcQ" },
    });
    await wrapper.find("[data-testid=\"play-button\"]").trigger("click");
    expect(wrapper.find("iframe").exists()).toBe(true);
    expect(wrapper.find("iframe").attributes("src")).toContain(
      "youtube.com/embed/dQw4w9WgXcQ",
    );
  });

  it("handles vimeo provider", async () => {
    const wrapper = mount(VideoEmbed, {
      props: { providerType: "vimeo", providerId: "123456" },
    });
    await wrapper.find("[data-testid=\"play-button\"]").trigger("click");
    expect(wrapper.find("iframe").attributes("src")).toContain(
      "player.vimeo.com/video/123456",
    );
  });
});
