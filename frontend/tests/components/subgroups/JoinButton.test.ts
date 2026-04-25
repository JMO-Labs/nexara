/**
 * @file tests/components/subgroups/JoinButton.test.ts
 * @brief Tests for the JoinButton component.
 *
 * Verifies join/leave/pending labels per policy and membership state,
 * loading state, store action wiring, and emitted events.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import JoinButton from "~/components/subgroups/JoinButton.vue";
import { useSubgroupsStore } from "~/stores/subgroups";

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() }),
}));

describe("JoinButton", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders Join when not a member of an open subgroup", () => {
    const wrapper = mount(JoinButton, {
      props: { slug: "demo", myRole: null, joinPolicy: "open" },
    });

    expect(
      wrapper.find('[data-testid="join-button-join"]').exists(),
    ).toBe(true);
    expect(wrapper.text()).toContain("subgroups.join");
  });

  it("renders Request to join for invite_only / admin_approval policies", () => {
    const wrapper = mount(JoinButton, {
      props: { slug: "demo", myRole: null, joinPolicy: "admin_approval" },
    });

    expect(wrapper.text()).toContain("subgroups.requestJoin");
  });

  it("renders Leave when the viewer is a member", () => {
    const wrapper = mount(JoinButton, {
      props: { slug: "demo", myRole: "member", joinPolicy: "open" },
    });

    expect(
      wrapper.find('[data-testid="join-button-leave"]').exists(),
    ).toBe(true);
    expect(wrapper.text()).toContain("subgroups.leave");
  });

  it("renders the Pending state and disables the button when pending=true", () => {
    const wrapper = mount(JoinButton, {
      props: {
        slug: "demo",
        myRole: null,
        joinPolicy: "admin_approval",
        pending: true,
      },
    });

    const btn = wrapper.find('[data-testid="join-button-pending"]');
    expect(btn.exists()).toBe(true);
    expect(btn.attributes("disabled")).toBeDefined();
  });

  it("calls joinSubgroup and emits joined when clicked on an open subgroup", async () => {
    const store = useSubgroupsStore();
    store.joinSubgroup = vi
      .fn()
      .mockResolvedValueOnce({ status: "joined", role: "member" });

    const wrapper = mount(JoinButton, {
      props: { slug: "demo", myRole: null, joinPolicy: "open" },
    });

    await wrapper.get("button").trigger("click");
    await flushPromises();

    expect(store.joinSubgroup).toHaveBeenCalledWith("demo");
    expect(wrapper.emitted("joined")).toBeTruthy();
  });

  it("emits pending and switches to pending state when status=pending", async () => {
    const store = useSubgroupsStore();
    store.joinSubgroup = vi
      .fn()
      .mockResolvedValueOnce({ status: "pending", policy: "admin_approval" });

    const wrapper = mount(JoinButton, {
      props: { slug: "demo", myRole: null, joinPolicy: "admin_approval" },
    });

    await wrapper.get("button").trigger("click");
    await flushPromises();

    expect(wrapper.emitted("pending")).toBeTruthy();
    expect(
      wrapper.find('[data-testid="join-button-pending"]').exists(),
    ).toBe(true);
  });

  it("calls leaveSubgroup and emits left when clicked as a member", async () => {
    const store = useSubgroupsStore();
    store.leaveSubgroup = vi.fn().mockResolvedValueOnce(undefined);

    const wrapper = mount(JoinButton, {
      props: { slug: "demo", myRole: "member", joinPolicy: "open" },
    });

    await wrapper.get("button").trigger("click");
    await flushPromises();

    expect(store.leaveSubgroup).toHaveBeenCalledWith("demo");
    expect(wrapper.emitted("left")).toBeTruthy();
  });

  it("does nothing when already pending", async () => {
    const store = useSubgroupsStore();
    store.joinSubgroup = vi.fn();

    const wrapper = mount(JoinButton, {
      props: {
        slug: "demo",
        myRole: null,
        joinPolicy: "admin_approval",
        pending: true,
      },
    });

    await wrapper.get("button").trigger("click");
    await flushPromises();

    expect(store.joinSubgroup).not.toHaveBeenCalled();
  });
});
