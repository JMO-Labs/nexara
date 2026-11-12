"use client";
/**
 * @file hooks/useRetention.ts
 * @brief TanStack Query hooks for admin retention policies.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { qk } from "@/lib/query-keys";
import * as api from "@/lib/api/retention";
import type { RetentionUpdate } from "@/lib/retention-policies";

/** @brief Fetch all retention policies. */
export const useRetentionPolicies = () =>
  useQuery({
    queryKey: qk.admin.retention(),
    queryFn: api.listRetentionPolicies,
    staleTime: 60 * 1000,
  });

/** @brief Update a policy; toasts and refetches the list. */
export const useUpdateRetention = () => {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: ({ key, body }: { key: string; body: RetentionUpdate }) =>
      api.updateRetentionPolicy(key, body),
    successKey: "toasts.admin.retention.updated",
    errorKey: "toasts.errors.generic",
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.admin.retention() }),
  });
};
