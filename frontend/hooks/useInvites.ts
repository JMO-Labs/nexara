'use client';
/**
 * @file hooks/useInvites.ts
 * @brief TanStack Query hooks for invite management.
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMutationWithToast } from './useMutationWithToast';
import { qk } from '@/lib/query-keys';
import * as invitesApi from '@/lib/api/invites';

/**
 * @brief Fetch all pending invites.
 */
export const useInvites = () =>
  useQuery({
    queryKey: qk.admin.invites(),
    queryFn: invitesApi.listInvites,
    staleTime: 30 * 1000, // 30 seconds
  });

/**
 * @brief Create a new invite. Invalidates useInvites on success.
 */
export const useCreateInvite = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: ({ email, role }: { email: string; role: string }) =>
      invitesApi.createInvite(email, role),
    successKey: 'toasts.invites.sent',
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.invites() });
    },
  });
};

/**
 * @brief Revoke an invite. Invalidates useInvites on success.
 */
export const useRevokeInvite = () => {
  const queryClient = useQueryClient();
  return useMutationWithToast({
    mutationFn: (inviteId: string) => invitesApi.revokeInvite(inviteId),
    successKey: 'toasts.invites.revoked',
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.admin.invites() });
    },
  });
};
