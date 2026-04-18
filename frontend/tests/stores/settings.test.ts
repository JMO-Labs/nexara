/**
 * @file tests/stores/settings.test.ts
 * @brief TDD tests for the settings Pinia store.
 *
 * Tests fetchSettings, updateSettings, updateProfile, and
 * updateNotificationPreferences. Mocks useApi() for HTTP calls.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useSettingsStore } from "~/stores/settings";
import { useAuthStore } from "~/stores/auth";
import type { UserSettingsResponse, User } from "~/types/api";

/** @brief Mock settings response from GET /settings/. */
const mockSettings: UserSettingsResponse = {
  notif_mention_inapp: true,
  notif_mention_email: false,
  notif_comment_inapp: true,
  notif_comment_email: true,
  notif_reaction_inapp: false,
  notif_reaction_email: false,
  notif_new_post_inapp: true,
  notif_new_post_email: false,
  notif_system_inapp: true,
  notif_system_email: false,
  notif_invite_accepted_inapp: false,
  notif_invite_accepted_email: false,
  mute_all_email: false,
  theme: "system",
  locale: "en-US",
};

/** @brief Mock user for auth store. */
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
  storage_used: 0,
  storage_quota: 1073741824,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  last_seen_at: null,
};

const mockGet = vi.fn();
const mockPut = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({
    get: mockGet,
    post: mockPut,
    put: mockPut,
    del: vi.fn(),
  }),
}));

describe("settings store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockGet.mockResolvedValue({ ...mockSettings });
    mockPut.mockResolvedValue({ ...mockSettings });
  });

  it("starts with null settings and loading false", () => {
    const store = useSettingsStore();

    expect(store.settings).toBeNull();
    expect(store.loading).toBe(false);
  });

  it("fetchSettings() loads settings from API", async () => {
    const store = useSettingsStore();
    mockGet.mockResolvedValueOnce(mockSettings);

    await store.fetchSettings();

    expect(mockGet).toHaveBeenCalledWith("/settings/");
    expect(store.settings).toEqual(mockSettings);
    expect(store.loading).toBe(false);
  });

  it("updateSettings() sends PUT and updates state", async () => {
    const store = useSettingsStore();
    store.settings = { ...mockSettings };
    const updated = { ...mockSettings, theme: "dark" };
    mockPut.mockResolvedValueOnce(updated);

    await store.updateSettings({ theme: "dark" });

    expect(mockPut).toHaveBeenCalledWith(
      "/settings/",
      expect.objectContaining({ theme: "dark" }),
    );
    expect(store.settings?.theme).toBe("dark");
  });

  it("updateProfile() calls PUT /settings/profile and fetches user", async () => {
    const store = useSettingsStore();
    const authStore = useAuthStore();
    authStore.accessToken = "token";
    authStore.user = { ...mockUser };
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockUser), { status: 200 }),
    );

    await store.updateProfile({ display_name: "Alice Updated" });

    expect(mockPut).toHaveBeenCalledWith("/settings/profile", {
      display_name: "Alice Updated",
    });
  });

  it("updateNotificationPreferences() sends PUT and updates state", async () => {
    const store = useSettingsStore();
    store.settings = { ...mockSettings };
    const updated = { ...mockSettings, notif_mention_email: true };
    mockPut.mockResolvedValueOnce(updated);

    await store.updateNotificationPreferences({ notif_mention_email: true });

    expect(mockPut).toHaveBeenCalledWith(
      "/settings/notifications",
      expect.objectContaining({ notif_mention_email: true }),
    );
    expect(store.settings?.notif_mention_email).toBe(true);
  });
});
