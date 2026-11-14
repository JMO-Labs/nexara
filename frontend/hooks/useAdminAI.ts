"use client";
/**
 * @file hooks/useAdminAI.ts
 * @brief TanStack Query hooks for the admin AI configuration tab.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import * as api from "@/lib/api/adminAI";

/** @brief Fetch and cache the AI config. */
export const useAdminAIConfig = () =>
  useQuery({
    queryKey: [...qk.admin.ai(), "config"],
    queryFn: api.getAIConfig,
  });

/** @brief Fetch AI usage metrics. */
export const useAdminAIMetrics = () =>
  useQuery({
    queryKey: [...qk.admin.ai(), "metrics"],
    queryFn: api.getAIMetrics,
    staleTime: 60 * 1000,
  });

/** @brief Update Sassybot settings; refreshes the cached config on success. */
export const useUpdateAdminAIConfig = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: api.AIConfigUpdate) => api.updateAIConfig(config),
    onSuccess: (data) => qc.setQueryData([...qk.admin.ai(), "config"], data),
  });
};

/** @brief Test the provider connection. */
export const useTestAIConnection = () =>
  useMutation({ mutationFn: api.testAIConnection });
