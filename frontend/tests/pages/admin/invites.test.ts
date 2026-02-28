/**
 * @file tests/pages/admin/invites.test.ts
 * @brief Tests for the admin invites page.
 *
 * Verifies create invite form submits correctly.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import AdminInvites from "~/pages/app/admin/invites.vue";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDel = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: mockGet,
    post: mockPost,
    del: mockDel,
  }),
}));

describe("Admin invites", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockGet.mockResolvedValue([]);
    mockPost.mockResolvedValue({
      id: "1",
      email: "new@example.com",
      role: "member",
    });
  });

  it("create invite form submits correctly", async () => {
    const wrapper = mount(AdminInvites);
    await flushPromises();

    await wrapper.find("#invite_email").setValue("new@example.com");
    await wrapper.find("#invite_role").setValue("member");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith("/admin/invites", {
      email: "new@example.com",
      role: "member",
    });
  });
});
