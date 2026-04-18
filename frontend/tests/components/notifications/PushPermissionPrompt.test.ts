/**
 * @file tests/components/notifications/PushPermissionPrompt.test.ts
 * @brief Tests for PushPermissionPrompt component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { ref } from "vue";
import { setActivePinia, createPinia } from "pinia";
import PushPermissionPrompt from "~/components/notifications/PushPermissionPrompt.vue";

const mockSubscribe = vi.fn();

vi.mock("~/composables/usePushNotifications", () => ({
  usePushNotifications: () => ({
    isSupported: ref(true),
    permission: ref("default"),
    subscribe: mockSubscribe,
    unsubscribe: vi.fn(),
    subscriptions: ref([]),
    loading: ref(false),
  }),
}));

describe("PushPermissionPrompt", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockSubscribe.mockReset();
  });

  it("renders enable and not now buttons", () => {
    const wrapper = mount(PushPermissionPrompt);
    expect(wrapper.text()).toContain("notifications.pushEnable");
    expect(wrapper.text()).toContain("notifications.pushNotNow");
  });

  it("calls subscribe when enable clicked", async () => {
    const wrapper = mount(PushPermissionPrompt);
    const enableBtn = wrapper.findAll("button").find((b) =>
      b.text().includes("pushEnable"),
    );
    expect(enableBtn).toBeDefined();
    await enableBtn!.trigger("click");
    expect(mockSubscribe).toHaveBeenCalled();
  });
});
