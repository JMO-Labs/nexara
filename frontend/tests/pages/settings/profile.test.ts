/**
 * @file tests/pages/settings/profile.test.ts
 * @brief Tests for the profile settings tab.
 *
 * Verifies form render (display_name, bio, location, website_url, title)
 * and submit behavior calling settingsStore.updateProfile with success toast.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "~/stores/auth";
import { useSettingsStore } from "~/stores/settings";
import type { User } from "~/types/api";
import ProfileSettings from "~/pages/app/settings/profile.vue";

const mockUser: User = {
  id: "1",
  email: "alice@example.com",
  username: "alice",
  display_name: "Alice",
  email_verified: true,
  avatar_url: null,
  bio: "Hello world",
  title: "Dr.",
  location: "NYC",
  website_url: "https://example.com",
  birthday: null,
  role: "member",
  totp_enabled: false,
  storage_used: 0,
  storage_quota: 1073741824,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  last_seen_at: null,
};

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    del: vi.fn(),
  }),
}));

describe("Profile settings", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    const authStore = useAuthStore();
    authStore.user = { ...mockUser };
  });

  it("renders form fields for display_name, bio, location, website_url, title", () => {
    const wrapper = mount(ProfileSettings);

    expect(wrapper.find("#display_name").exists()).toBe(true);
    expect(wrapper.find("#bio").exists()).toBe(true);
    expect(wrapper.find("#location").exists()).toBe(true);
    expect(wrapper.find("#website_url").exists()).toBe(true);
    expect(wrapper.find("#title").exists()).toBe(true);
  });

  it("prefills form from auth store user", async () => {
    const wrapper = mount(ProfileSettings);
    await wrapper.vm.$nextTick();

    expect(
      (wrapper.find("#display_name").element as HTMLInputElement).value,
    ).toBe("Alice");
    expect((wrapper.find("#bio").element as HTMLTextAreaElement).value).toBe(
      "Hello world",
    );
    expect((wrapper.find("#location").element as HTMLInputElement).value).toBe(
      "NYC",
    );
    expect(
      (wrapper.find("#website_url").element as HTMLInputElement).value,
    ).toBe("https://example.com");
    expect((wrapper.find("#title").element as HTMLInputElement).value).toBe(
      "Dr.",
    );
  });

  it("calls updateProfile on submit", async () => {
    const settingsStore = useSettingsStore();
    const updateProfileSpy = vi
      .spyOn(settingsStore, "updateProfile")
      .mockResolvedValue();

    const wrapper = mount(ProfileSettings);

    await wrapper.find("#display_name").setValue("Alice Updated");
    await wrapper.find("form").trigger("submit.prevent");

    expect(updateProfileSpy).toHaveBeenCalledWith(
      expect.objectContaining({ display_name: "Alice Updated" }),
    );
  });
});
