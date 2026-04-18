/**
 * @file tests/pages/admin/branding.test.ts
 * @brief Tests for admin branding page.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "~/stores/auth";
import BrandingPage from "~/pages/app/admin/branding.vue";
import ColorPicker from "~/components/admin/ColorPicker.vue";
import FontPicker from "~/components/admin/FontPicker.vue";
import BrandingPreview from "~/components/admin/BrandingPreview.vue";
import type { User } from "~/types/api";

const mockAdminUser: User = {
  id: "1",
  email: "admin@example.com",
  username: "admin",
  display_name: "Admin",
  email_verified: true,
  avatar_url: null,
  bio: null,
  title: null,
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
};

const mockGet = vi.fn();
const mockPut = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({ get: mockGet, post: vi.fn(), put: mockPut, del: vi.fn() }),
}));

describe("Admin Branding Page", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const authStore = useAuthStore();
    authStore.user = { ...mockAdminUser };
    mockGet.mockReset();
    mockPut.mockReset();
  });

  it("loads branding on mount", async () => {
    mockGet.mockResolvedValue({
      community_name: "Test",
      color_primary: "#3b82f6",
      color_primary_dark: "#2563eb",
    });

    mount(BrandingPage, {
      global: {
        components: {
          AdminColorPicker: ColorPicker,
          AdminFontPicker: FontPicker,
          AdminBrandingPreview: BrandingPreview,
        },
      },
    });

    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith("/branding/");
  });

  it("shows contrast warnings from update response", async () => {
    mockGet.mockResolvedValue({
      community_name: "Test",
      color_primary: "#3b82f6",
      color_primary_dark: "#2563eb",
    });
    mockPut.mockResolvedValue({
      branding: { community_name: "Test" },
      contrast_warnings: [
        {
          color1: "#111827",
          color2: "#ffffff",
          ratio: 16.1,
          passes_aa: true,
          passes_aaa: true,
        },
      ],
    });

    const wrapper = mount(BrandingPage, {
      global: {
        components: {
          AdminColorPicker: ColorPicker,
          AdminFontPicker: FontPicker,
          AdminBrandingPreview: BrandingPreview,
        },
      },
    });

    await flushPromises();

    const submitBtn = wrapper.find("[data-testid=\"branding-submit\"]");
    expect(submitBtn.exists()).toBe(true);
  });
});
