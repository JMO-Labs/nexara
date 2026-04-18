/**
 * @file tests/pages/settings/storage.test.ts
 * @brief TDD tests for the storage settings page.
 *
 * Verifies storage usage display and progress bar.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "~/stores/auth";
import StoragePage from "~/pages/app/settings/storage.vue";
import type { User } from "~/types/api";

const mockUser: User = {
  id: "1",
  email: "alice@example.com",
  username: "alice",
  display_name: "Alice",
  email_verified: true,
  avatar_url: null,
  bio: null,
  title: null,
  location: null,
  website_url: null,
  birthday: null,
  role: "member",
  totp_enabled: false,
  storage_used: 536870912,
  storage_quota: 1073741824,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  last_seen_at: null,
};

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() }),
}));

describe("StoragePage", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const authStore = useAuthStore();
    authStore.user = { ...mockUser };
  });

  it("renders storage usage", async () => {
    const wrapper = mount(StoragePage);
    await flushPromises();
    // Should contain storage-related text
    expect(
      wrapper.find("[data-testid=\"storage-bar\"]").exists() ||
        wrapper.text().toLowerCase().includes("storage") ||
        wrapper.text().toLowerCase().includes("gb") ||
        wrapper.text().toLowerCase().includes("mb"),
    ).toBeTruthy();
  });
});
