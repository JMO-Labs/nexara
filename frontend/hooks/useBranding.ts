"use client";
/**
 * @file hooks/useBranding.ts
 * @brief TanStack Query hooks for community branding.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { useToasts } from "@/stores/toasts";
import { qk } from "@/lib/query-keys";
import * as brandingApi from "@/lib/api/branding";

/** @brief Fetch branding. */
export const useBranding = () =>
  useQuery({
    queryKey: qk.admin.branding(),
    queryFn: brandingApi.getBranding,
    staleTime: 5 * 60 * 1000,
  });

/** @brief Update branding; refreshes the cache and toasts on success. */
export const useUpdateBranding = () => {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  return useMutationWithToast({
    mutationFn: brandingApi.updateBranding,
    silentError: true,
    silentSuccess: true,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.admin.branding() });
      push({ variant: "success", message: "Branding saved" });
    },
  });
};
