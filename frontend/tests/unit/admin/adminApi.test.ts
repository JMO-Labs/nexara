/**
 * @file tests/unit/admin/adminApi.test.ts
 * @brief Tests for admin API wrapper functions.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as client from "@/lib/api/client";
import {
  getMetrics,
  listAdminUsers,
  changeUserRole,
  suspendUser,
  restoreUser,
  deleteUser,
  getAdminSettings,
  updateAdminSettings,
  getAuditLog,
} from "@/lib/api/admin";

vi.mock("@/lib/api/client");

describe("adminApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getMetrics", () => {
    it("should call apiGet with correct path", async () => {
      const mockMetrics = {
        community: {
          users_total: 10,
          users_active_30d: 5,
          users_online_now: 2,
          posts_total: 100,
          posts_last_7d: 20,
          media_files: 50,
          media_storage_bytes: 1000000,
        },
        system: {
          version: "1.0.0",
          uptime_seconds: 86400,
          db_size_bytes: 5000000,
          valkey_memory_bytes: 512000,
          celery_queue_depth: 10,
        },
        waf: {
          blocks_today: 5,
          blocks_by_reason: { "sql-injection": 3, xss: 2 },
        },
      };
      vi.mocked(client.apiGet).mockResolvedValue(mockMetrics);

      const result = await getMetrics();

      expect(client.apiGet).toHaveBeenCalledWith("/api/v1/admin/metrics");
      expect(result).toEqual(mockMetrics);
    });
  });

  describe("listAdminUsers", () => {
    it("should call apiGet with filters", async () => {
      const mockUsers = {
        items: [
          {
            id: "user-1",
            username: "john",
            display_name: "John Doe",
            email: "john@example.com",
            avatar_url: null,
            bio: null,
            title: null,
            location: null,
            website_url: null,
            role: "member",
            created_at: new Date(),
            last_seen_at: new Date(),
            status: "active",
          },
        ],
        next_cursor: null,
        has_more: false,
      };
      vi.mocked(client.apiGet).mockResolvedValue(mockUsers);

      const result = await listAdminUsers({
        q: "john",
        limit: 20,
        cursor: null,
      });

      expect(client.apiGet).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/admin/users?"),
      );
      expect(result).toEqual(mockUsers);
    });
  });

  describe("changeUserRole", () => {
    it("should call apiPut with user id and role", async () => {
      const mockResponse = { message: "Role updated" };
      vi.mocked(client.apiPut).mockResolvedValue(mockResponse);

      const result = await changeUserRole("user-1", "admin");

      expect(client.apiPut).toHaveBeenCalledWith(
        "/api/v1/admin/users/user-1/role",
        { role: "admin" },
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe("suspendUser", () => {
    it("should call apiPost with user id", async () => {
      const mockResponse = { message: "User suspended" };
      vi.mocked(client.apiPost).mockResolvedValue(mockResponse);

      const result = await suspendUser("user-1");

      expect(client.apiPost).toHaveBeenCalledWith(
        "/api/v1/admin/users/user-1/suspend",
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe("restoreUser", () => {
    it("should call apiPost with user id", async () => {
      const mockResponse = { message: "User restored" };
      vi.mocked(client.apiPost).mockResolvedValue(mockResponse);

      const result = await restoreUser("user-1");

      expect(client.apiPost).toHaveBeenCalledWith(
        "/api/v1/admin/users/user-1/restore",
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe("deleteUser", () => {
    it("should call apiDelete with user id", async () => {
      const mockResponse = { message: "User deleted" };
      vi.mocked(client.apiDelete).mockResolvedValue(mockResponse);

      const result = await deleteUser("user-1");

      expect(client.apiDelete).toHaveBeenCalledWith(
        "/api/v1/admin/users/user-1",
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe("getAdminSettings", () => {
    it("should call apiGet with correct path", async () => {
      const mockSettings = {
        enable_registration: true,
        require_invite: false,
        storage_quota_default: 5000000000,
        waf_enabled: true,
      };
      vi.mocked(client.apiGet).mockResolvedValue(mockSettings);

      const result = await getAdminSettings();

      expect(client.apiGet).toHaveBeenCalledWith("/api/v1/admin/settings");
      expect(result).toEqual(mockSettings);
    });
  });

  describe("updateAdminSettings", () => {
    it("should call apiPut with partial settings", async () => {
      const mockSettings = {
        enable_registration: true,
        require_invite: false,
        storage_quota_default: 5000000000,
        waf_enabled: true,
      };
      vi.mocked(client.apiPut).mockResolvedValue(mockSettings);

      const result = await updateAdminSettings({ enable_registration: false });

      expect(client.apiPut).toHaveBeenCalledWith("/api/v1/admin/settings", {
        enable_registration: false,
      });
      expect(result).toEqual(mockSettings);
    });
  });

  describe("getAuditLog", () => {
    it("should call apiGet with filters", async () => {
      const mockAuditLog = {
        items: [
          {
            id: "audit-1",
            actor_id: "user-1",
            actor_display_name: "Admin User",
            action: "user_role_changed",
            target_type: "user",
            target_id: "user-2",
            target_display: "John Doe",
            extra_data: { old_role: "member", new_role: "admin" },
            ip_address: "127.0.0.1",
            created_at: new Date(),
          },
        ],
        next_cursor: null,
        has_more: false,
      };
      vi.mocked(client.apiGet).mockResolvedValue(mockAuditLog);

      const result = await getAuditLog({ limit: 50, cursor: null });

      expect(client.apiGet).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/admin/audit-log?"),
      );
      expect(result).toEqual(mockAuditLog);
    });
  });
});
