/**
 * @file tests/components/content/LinkPreviewCard.test.ts
 * @brief TDD tests for the LinkPreviewCard component.
 *
 * Verifies title, description, image display, and link to URL.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import LinkPreviewCard from "~/components/content/LinkPreviewCard.vue";

describe("LinkPreviewCard", () => {
  const preview = {
    id: "lp-1",
    url: "https://example.com",
    title: "Example Site",
    description: "A great website",
    image_url: "https://example.com/og.jpg",
    site_name: "Example",
    provider_type: null,
    provider_id: null,
  };

  it("renders title and description", () => {
    const wrapper = mount(LinkPreviewCard, { props: { preview } });
    expect(wrapper.text()).toContain("Example Site");
    expect(wrapper.text()).toContain("A great website");
  });

  it("renders image when provided", () => {
    const wrapper = mount(LinkPreviewCard, { props: { preview } });
    expect(wrapper.find("img").exists()).toBe(true);
  });

  it("links to url", () => {
    const wrapper = mount(LinkPreviewCard, { props: { preview } });
    const link = wrapper.find("a");
    expect(link.attributes("href")).toBe("https://example.com");
  });
});
