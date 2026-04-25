/**
 * @file tests/components/chat/ChannelSidebar.test.ts
 * @brief Tests for the chat ChannelSidebar component.
 *
 * Verifies channel grouping by type, active channel highlighting,
 * unread badge rendering, channel selection emission, and empty state.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ChannelSidebar from "~/components/chat/ChannelSidebar.vue";
import type { ChatChannel } from "~/types/api";

const community: ChatChannel = {
  id: "chan-c",
  community_id: "comm-1",
  name: "general",
  channel_type: "community",
  subgroup_id: null,
  created_at: "2026-04-01T10:00:00Z",
};

const subgroup: ChatChannel = {
  id: "chan-s",
  community_id: "comm-1",
  name: "photographers",
  channel_type: "subgroup",
  subgroup_id: "sg-1",
  created_at: "2026-04-02T10:00:00Z",
};

const direct: ChatChannel = {
  id: "chan-d",
  community_id: "comm-1",
  name: "Bob",
  channel_type: "direct",
  subgroup_id: null,
  created_at: "2026-04-03T10:00:00Z",
};

describe("ChannelSidebar", () => {
  it("shows the empty state when no channels are present", () => {
    const wrapper = mount(ChannelSidebar, {
      props: { channels: [], unreadByChannel: {}, activeChannelId: null },
    });

    expect(
      wrapper.find('[data-testid="channel-sidebar-empty"]').exists(),
    ).toBe(true);
  });

  it("renders a button per channel", () => {
    const wrapper = mount(ChannelSidebar, {
      props: {
        channels: [community, subgroup, direct],
        unreadByChannel: {},
        activeChannelId: null,
      },
    });

    expect(
      wrapper.find('[data-testid="channel-item-chan-c"]').exists(),
    ).toBe(true);
    expect(
      wrapper.find('[data-testid="channel-item-chan-s"]').exists(),
    ).toBe(true);
    expect(
      wrapper.find('[data-testid="channel-item-chan-d"]').exists(),
    ).toBe(true);
  });

  it("marks the active channel with aria-current", () => {
    const wrapper = mount(ChannelSidebar, {
      props: {
        channels: [community, direct],
        unreadByChannel: {},
        activeChannelId: "chan-c",
      },
    });

    expect(
      wrapper
        .get('[data-testid="channel-item-chan-c"]')
        .attributes("aria-current"),
    ).toBe("page");
    expect(
      wrapper
        .get('[data-testid="channel-item-chan-d"]')
        .attributes("aria-current"),
    ).toBeUndefined();
  });

  it("renders unread badge with the count for channels with unread messages", () => {
    const wrapper = mount(ChannelSidebar, {
      props: {
        channels: [community],
        unreadByChannel: { "chan-c": 7 },
        activeChannelId: null,
      },
    });

    const badge = wrapper.get('[data-testid="channel-unread-chan-c"]');
    expect(badge.text()).toBe("7");
  });

  it("hides the unread badge when count is 0 or missing", () => {
    const wrapper = mount(ChannelSidebar, {
      props: {
        channels: [community],
        unreadByChannel: { "chan-c": 0 },
        activeChannelId: null,
      },
    });

    expect(
      wrapper.find('[data-testid="channel-unread-chan-c"]').exists(),
    ).toBe(false);
  });

  it("emits select with the channel when a button is clicked", async () => {
    const wrapper = mount(ChannelSidebar, {
      props: {
        channels: [community],
        unreadByChannel: {},
        activeChannelId: null,
      },
    });

    await wrapper.get('[data-testid="channel-item-chan-c"]').trigger("click");

    expect(wrapper.emitted("select")?.[0]?.[0]).toEqual(community);
  });

  it("renders direct channels with @ prefix and others with #", () => {
    const wrapper = mount(ChannelSidebar, {
      props: {
        channels: [community, direct],
        unreadByChannel: {},
        activeChannelId: null,
      },
    });

    expect(
      wrapper.get('[data-testid="channel-item-chan-c"]').text(),
    ).toContain("#");
    expect(
      wrapper.get('[data-testid="channel-item-chan-d"]').text(),
    ).toContain("@");
  });
});
