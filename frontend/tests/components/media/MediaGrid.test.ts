/**
 * @file tests/components/media/MediaGrid.test.ts
 * @brief TDD tests for the MediaGrid component.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import MediaGrid from "~/components/media/MediaGrid.vue";

const mockItems = [
  {
    id: "1",
    url: "/img/1.jpg",
    thumbnail_url: "/thumb/1.jpg",
    mime_type: "image/jpeg",
    width: 800,
    height: 600,
  },
  {
    id: "2",
    url: "/img/2.jpg",
    thumbnail_url: "/thumb/2.jpg",
    mime_type: "image/png",
    width: 640,
    height: 480,
  },
  {
    id: "3",
    url: "/img/3.jpg",
    thumbnail_url: "/thumb/3.jpg",
    mime_type: "image/webp",
    width: 1024,
    height: 768,
  },
];

describe("MediaGrid", () => {
  it("renders correct number of thumbnails", () => {
    const wrapper = mount(MediaGrid, {
      props: { items: mockItems },
    });

    expect(wrapper.findAll("button")).toHaveLength(3);
    expect(wrapper.findAll("img")).toHaveLength(3);
  });

  it("emits open event with index on thumbnail click", async () => {
    const wrapper = mount(MediaGrid, {
      props: { items: mockItems },
    });

    await wrapper.findAll("button")[1].trigger("click");
    expect(wrapper.emitted("open")![0]).toEqual([1]);
  });
});
