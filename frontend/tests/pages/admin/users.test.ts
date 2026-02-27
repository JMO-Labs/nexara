/**
 * @file tests/pages/admin/users.test.ts
 * @brief Tests for the admin users page.
 *
 * Verifies user table with role badges and role change action.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import AdminUsers from "~/pages/app/admin/users.vue";
import AdminUserTable from "~/components/admin/UserTable.vue";
import type { AdminUserListItem } from "~/types/api";

const mockUsers: AdminUserListItem[] = [
  {
    id: "1",
    email: "alice@example.com",
    username: "alice",
    display_name: "Alice",
    email_verified: true,
    avatar_url: null,
    bio: null,
    pronouns: null,
    location: null,
    website_url: null,
    birthday: null,
    role: "admin",
    totp_enabled: false,
    storage_used: 0,
    storage_quota: 1073741824,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    last_seen_at: null,
    status: "active",
  },
  {
    id: "2",
    email: "bob@example.com",
    username: "bob",
    display_name: "Bob",
    email_verified: true,
    avatar_url: null,
    bio: null,
    pronouns: null,
    location: null,
    website_url: null,
    birthday: null,
    role: "member",
    totp_enabled: false,
    storage_used: 0,
    storage_quota: 1073741824,
    created_at: "2026-01-02T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
    last_seen_at: null,
    status: "active",
  },
];

const mockGet = vi.fn();
const mockPut = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: mockGet,
    put: mockPut,
    post: vi.fn(),
    del: vi.fn(),
  }),
}));

describe("Admin users", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ items: mockUsers, has_more: false });
    vi.stubGlobal(
      "prompt",
      vi.fn(() => "member"),
    );
  });

  it("renders user table with role badges", async () => {
    const wrapper = mount(AdminUsers, {
      global: { components: { AdminUserTable } },
    });
    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith(
      expect.stringContaining("/admin/users"),
    );
    expect(wrapper.text()).toContain("alice@example.com");
    expect(wrapper.text()).toContain("bob@example.com");
    expect(wrapper.text()).toContain("admin");
    expect(wrapper.text()).toContain("member");
  });

  it("role change action triggers API call", async () => {
    mockPut.mockResolvedValue({});
    mockGet.mockResolvedValue({ items: mockUsers, has_more: false });
    const wrapper = mount(AdminUsers, {
      global: { components: { AdminUserTable } },
    });
    await flushPromises();

    const userTable = wrapper.findComponent(AdminUserTable);
    expect(userTable.exists()).toBe(true);
    await userTable.vm.$emit("change-role", mockUsers[0]);
    await flushPromises();

    expect(mockPut).toHaveBeenCalledWith(
      "/admin/users/1/role",
      expect.objectContaining({ role: "member" }),
    );
  });
});
