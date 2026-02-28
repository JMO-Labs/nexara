/**
 * @file tests/pages/admin/dashboard.test.ts
 * @brief Tests for the admin dashboard page.
 *
 * Verifies metrics cards render with data from /admin/metrics.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "~/stores/auth";
import AdminDashboard from "~/pages/app/admin/index.vue";
import MetricsCard from "~/components/admin/MetricsCard.vue";
import AuditLogTable from "~/components/admin/AuditLogTable.vue";
import type { User } from "~/types/api";

const mockAdminUser: User = {
  id: "1",
  email: "admin@example.com",
  username: "admin",
  display_name: "Admin",
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
};

/** @brief Nested API response from GET /admin/metrics. */
const mockMetricsApiResponse = {
  community: {
    users_total: 42,
    users_active_30d: 15,
    users_online_now: 3,
    posts_total: 120,
    posts_last_7d: 8,
    media_files: 45,
    media_storage_bytes: 1073741824,
  },
  system: { version: "0.1.0", uptime_seconds: 3600 },
  waf: { blocks_today: 5, blocks_by_reason: {} },
};

const mockGet = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({ get: mockGet }),
}));

describe("Admin dashboard", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    const authStore = useAuthStore();
    authStore.user = { ...mockAdminUser };
    mockGet
      .mockResolvedValueOnce(mockMetricsApiResponse)
      .mockResolvedValueOnce({ items: [] });
  });

  it("renders metrics cards with data", async () => {
    const wrapper = mount(AdminDashboard, {
      global: {
        components: {
          AdminMetricsCard: MetricsCard,
          AdminAuditLogTable: AuditLogTable,
        },
      },
    });
    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith("/admin/metrics");
    expect(mockGet).toHaveBeenCalledWith("/admin/audit-log?limit=5");

    const cards = wrapper.findAllComponents(MetricsCard);
    expect(cards.length).toBeGreaterThanOrEqual(7);
    expect(wrapper.text()).toContain("42");
    expect(wrapper.text()).toContain("15");
    expect(wrapper.text()).toContain("3");
  });
});
