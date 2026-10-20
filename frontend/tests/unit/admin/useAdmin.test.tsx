/**
 * @file tests/unit/admin/useAdmin.test.tsx
 * @brief Tests for admin TanStack Query hooks with mutation invalidation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as adminApi from "@/lib/api/admin";
import {
  useAdminMetrics,
  useAdminUsers,
  useAdminSettings,
  useAuditLog,
  useChangeUserRole,
  useSuspendUser,
  useRestoreUser,
  useDeleteUser,
  useUpdateAdminSettings,
} from "@/hooks/useAdmin";
import { useToasts } from "@/stores/toasts";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      "toasts.admin.user.updated": "User updated",
      "toasts.admin.user.deactivated": "User deactivated",
      "toasts.errors.generic": "Something went wrong",
    };
    return translations[key] || key;
  },
}));

vi.mock("@/lib/api/admin");

describe("useAdmin hooks", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
    useToasts.getState().clear();
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "Wrapper";
  const wrapper = Wrapper;

  describe("useAdminMetrics", () => {
    it("should fetch metrics", async () => {
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
          db_size_bytes: null,
          valkey_memory_bytes: null,
          celery_queue_depth: null,
        },
        waf: { blocks_today: 5, blocks_by_reason: {} },
      };
      vi.mocked(adminApi.getMetrics).mockResolvedValue(mockMetrics);

      const { result } = renderHook(() => useAdminMetrics(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockMetrics);
    });
  });

  describe("useAdminUsers", () => {
    it("should fetch users with filters", async () => {
      const mockUsers = {
        items: [],
        next_cursor: null,
        has_more: false,
      };
      vi.mocked(adminApi.listAdminUsers).mockResolvedValue(mockUsers);

      const { result } = renderHook(() => useAdminUsers({ q: "john" }), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockUsers);
      expect(adminApi.listAdminUsers).toHaveBeenCalledWith({ q: "john" });
    });
  });

  describe("useChangeUserRole mutation", () => {
    it("should invalidate users query on success", async () => {
      vi.mocked(adminApi.changeUserRole).mockResolvedValue({
        message: "updated",
      });
      const getSpy = vi.spyOn(adminApi, "listAdminUsers");

      const { result } = renderHook(() => useChangeUserRole(), { wrapper });

      await waitFor(() => {
        result.current.mutate({ userId: "user-1", role: "admin" });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(adminApi.changeUserRole).toHaveBeenCalledWith("user-1", "admin");
    });
  });

  describe("useSuspendUser mutation", () => {
    it("should call suspend endpoint", async () => {
      vi.mocked(adminApi.suspendUser).mockResolvedValue({
        message: "suspended",
      });

      const { result } = renderHook(() => useSuspendUser(), { wrapper });

      await waitFor(() => {
        result.current.mutate("user-1");
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(adminApi.suspendUser).toHaveBeenCalledWith("user-1");
    });
  });

  describe("useRestoreUser mutation", () => {
    it("should call restore endpoint", async () => {
      vi.mocked(adminApi.restoreUser).mockResolvedValue({
        message: "restored",
      });

      const { result } = renderHook(() => useRestoreUser(), { wrapper });

      await waitFor(() => {
        result.current.mutate("user-1");
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(adminApi.restoreUser).toHaveBeenCalledWith("user-1");
    });
  });

  describe("useDeleteUser mutation", () => {
    it("should call delete endpoint", async () => {
      vi.mocked(adminApi.deleteUser).mockResolvedValue({ message: "deleted" });

      const { result } = renderHook(() => useDeleteUser(), { wrapper });

      await waitFor(() => {
        result.current.mutate("user-1");
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(adminApi.deleteUser).toHaveBeenCalledWith("user-1");
    });
  });

  describe("useUpdateAdminSettings mutation", () => {
    it("should invalidate settings query on success", async () => {
      const mockSettings = {
        enable_registration: false,
        require_invite: true,
        storage_quota_default: 5000000000,
        waf_enabled: true,
      };
      vi.mocked(adminApi.updateAdminSettings).mockResolvedValue(mockSettings);

      const { result } = renderHook(() => useUpdateAdminSettings(), {
        wrapper,
      });

      await waitFor(() => {
        result.current.mutate({ enable_registration: false });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(adminApi.updateAdminSettings).toHaveBeenCalledWith({
        enable_registration: false,
      });
    });
  });
});
