"use client";
/**
 * @file hooks/useAdmin.ts
 * @brief TanStack Query hooks for admin panel operations (queries + mutations).
 *        Mutations invalidate their sibling queries on success.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { qk } from "@/lib/query-keys";
import * as adminApi from "@/lib/api/admin";

/**
 * @brief Fetch community/system/WAF metrics.
 */
export const useAdminMetrics = () =>
  useQuery({
    queryKey: qk.admin.metrics(),
    queryFn: adminApi.getMetrics,
    staleTime: 60 * 1000, // 1 minute
  });

/**
 * @brief Fetch admin users with optional filters.
 */
export const useAdminUsers = (filters?: {
  q?: string;
  limit?: number;
  cursor?: string | null;
}) =>
  useQuery({
    queryKey: qk.admin.users(filters),
    queryFn: () => adminApi.listAdminUsers(filters),
    staleTime: 30 * 1000, // 30 seconds
  });

/**
 * @brief Fetch admin settings.
 */
export const useAdminSettings = () =>
  useQuery({
    queryKey: qk.admin.settings(),
    queryFn: adminApi.getAdminSettings,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

/**
 * @brief Fetch audit log entries.
 */
export const useAuditLog = (filters?: {
  limit?: number;
  cursor?: string | null;
}) =>
  useQuery({
    queryKey: qk.admin.auditLog(),
    queryFn: () => adminApi.getAuditLog(filters),
    staleTime: 60 * 1000, // 1 minute
  });

/**
 * @brief Change a user's role. Invalidates useAdminUsers on success.
 */
export const useChangeUserRole = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      adminApi.changeUserRole(userId, role),
    successKey: "toasts.admin.user.updated",
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.users() });
    },
  });
};

/**
 * @brief Suspend a user. Invalidates useAdminUsers on success.
 */
export const useSuspendUser = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: (userId: string) => adminApi.suspendUser(userId),
    successKey: "toasts.admin.user.deactivated",
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.users() });
    },
  });
};

/**
 * @brief Restore a suspended user. Invalidates useAdminUsers on success.
 */
export const useRestoreUser = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: (userId: string) => adminApi.restoreUser(userId),
    successKey: "toasts.admin.user.restored",
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.users() });
    },
  });
};

/**
 * @brief Delete a user. Invalidates useAdminUsers on success.
 */
export const useDeleteUser = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: (userId: string) => adminApi.deleteUser(userId),
    successKey: "toasts.admin.user.deleted",
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.users() });
    },
  });
};

/**
 * @brief Update admin settings. Invalidates useAdminSettings on success.
 */
export const useUpdateAdminSettings = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: (updates: adminApi.AdminSettingsUpdate) =>
      adminApi.updateAdminSettings(updates),
    successKey: "toasts.admin.settings.saved",
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.settings() });
    },
  });
};
