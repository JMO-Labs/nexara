"use client";
/**
 * @file hooks/useAdminOauth.ts
 * @brief TanStack Query hooks for OAuth provider management.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { qk } from "@/lib/query-keys";
import * as oauthApi from "@/lib/api/adminOauth";

/**
 * @brief Fetch all OAuth providers.
 */
export const useOauthProviders = () =>
  useQuery({
    queryKey: qk.admin.oauth(),
    queryFn: oauthApi.listOauthProviders,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

/**
 * @brief Create a new OAuth provider. Invalidates useOauthProviders on success.
 */
export const useCreateOauthProvider = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: (payload: oauthApi.OAuthProviderCreate) =>
      oauthApi.createOauthProvider(payload),
    successKey: "toasts.admin.user.updated",
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.oauth() });
    },
  });
};

/**
 * @brief Update an OAuth provider. Invalidates useOauthProviders on success.
 */
export const useUpdateOauthProvider = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: ({
      providerId,
      updates,
    }: {
      providerId: string;
      updates: oauthApi.OAuthProviderUpdate;
    }) => oauthApi.updateOauthProvider(providerId, updates),
    successKey: "toasts.admin.user.updated",
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.oauth() });
    },
  });
};

/**
 * @brief Delete an OAuth provider. Invalidates useOauthProviders on success.
 */
export const useDeleteOauthProvider = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: (providerId: string) =>
      oauthApi.deleteOauthProvider(providerId),
    successKey: "toasts.admin.user.updated",
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.oauth() });
    },
  });
};

/**
 * @brief Toggle OAuth provider enabled/disabled. Invalidates useOauthProviders on success.
 */
export const useToggleOauthProvider = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: (providerId: string) =>
      oauthApi.toggleOauthProvider(providerId),
    successKey: "toasts.admin.user.updated",
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.oauth() });
    },
  });
};

/**
 * @brief Discover OIDC endpoints from issuer URL.
 */
export const useDiscoverIssuer = () =>
  useMutationWithToast({
    mutationFn: (issuer: string) => oauthApi.discoverIssuer(issuer),
    silentSuccess: true,
  });
