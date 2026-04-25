/**
 * @file tests/unit/admin/useInvites.test.tsx
 * @brief Tests for invite TanStack Query hooks.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import * as invitesApi from '@/lib/api/invites';
import {
  useInvites,
  useCreateInvite,
  useRevokeInvite,
} from '@/hooks/useInvites';
import { useToasts } from '@/stores/toasts';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      'toasts.invites.sent': 'Invite sent',
      'toasts.invites.revoked': 'Invite revoked',
      'toasts.errors.generic': 'Something went wrong',
    };
    return translations[key] || key;
  },
}));

vi.mock('@/lib/api/invites');

describe('useInvites hooks', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    vi.clearAllMocks();
    useToasts.getState().clear();
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = 'Wrapper';
  const wrapper = Wrapper;

  describe('useInvites', () => {
    it('should fetch invites', async () => {
      const mockInvites = [
        {
          id: 'invite-1',
          email: 'test@example.com',
          role: 'member',
          created_at: new Date(),
          expires_at: new Date(),
          used_at: null,
          code: 'abc123',
        },
      ];
      vi.mocked(invitesApi.listInvites).mockResolvedValue(mockInvites);

      const { result } = renderHook(() => useInvites(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockInvites);
    });
  });

  describe('useCreateInvite mutation', () => {
    it('should create invite and invalidate list', async () => {
      const mockResponse = {
        id: 'invite-1',
        code: 'abc123',
        email: 'test@example.com',
        role: 'member',
      };
      vi.mocked(invitesApi.createInvite).mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useCreateInvite(), { wrapper });

      await waitFor(() => {
        result.current.mutate({ email: 'test@example.com', role: 'member' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(invitesApi.createInvite).toHaveBeenCalledWith(
        'test@example.com',
        'member',
      );
    });
  });

  describe('useRevokeInvite mutation', () => {
    it('should revoke invite and invalidate list', async () => {
      vi.mocked(invitesApi.revokeInvite).mockResolvedValue({ message: 'revoked' });

      const { result } = renderHook(() => useRevokeInvite(), { wrapper });

      await waitFor(() => {
        result.current.mutate('invite-1');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(invitesApi.revokeInvite).toHaveBeenCalledWith('invite-1');
    });
  });
});
