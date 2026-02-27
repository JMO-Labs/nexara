/**
 * @file tests/pages/admin/audit-log.test.ts
 * @brief Tests for the admin audit log page.
 *
 * Verifies audit entries render with filter dropdown.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import AdminAuditLog from "~/pages/app/admin/audit-log.vue";
import AdminAuditLogTable from "~/components/admin/AuditLogTable.vue";
import type { AuditLogEntry } from "~/types/api";

const mockEntries: AuditLogEntry[] = [
  {
    id: "1",
    actor_id: "user-1",
    actor_display_name: "Alice",
    action: "branding.updated",
    target_type: "branding",
    target_id: null,
    target_display: "Community logo",
    ip_address: "192.168.1.1",
    created_at: "2026-01-15T10:00:00Z",
  },
  {
    id: "2",
    actor_id: null,
    actor_display_name: null,
    action: "user.created",
    target_type: "user",
    target_id: "user-2",
    target_display: "Bob",
    ip_address: null,
    created_at: "2026-01-15T09:00:00Z",
  },
];

const mockGet = vi.fn();

vi.mock("~/composables/useApi", () => ({
  useApi: () => ({ get: mockGet }),
}));

describe("Admin audit log", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockGet.mockResolvedValue({
      items: mockEntries,
      next_cursor: null,
      has_more: false,
    });
  });

  it("renders audit entries with filter", async () => {
    const wrapper = mount(AdminAuditLog, {
      global: { components: { AdminAuditLogTable } },
    });
    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith(
      expect.stringContaining("/admin/audit-log"),
    );
    expect(wrapper.text()).toContain("branding.updated");
    expect(wrapper.text()).toContain("user.created");
    expect(wrapper.text()).toContain("Alice");
    expect(wrapper.text()).toContain("Community logo");

    const filterSelect = wrapper.find("select");
    expect(filterSelect.exists()).toBe(true);
    expect(filterSelect.findAll("option").length).toBeGreaterThan(1);
  });
});
