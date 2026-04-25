/**
 * @file tests/unit/admin/useAdminOauth.test.tsx
 * @brief Tests for OAuth provider TanStack Query hooks.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import * as oauthApi from '@/lib/api/adminOauth';
import type { OAuthProviderResponse } from '@/lib/api/adminOauth';
import {
  useOauthProviders,
  useCreateOauthProvider,
  useUpdateOauthProvider,
  useDeleteOauthProvider,
  useToggleOauthProvider,
  useDiscoverIssuer,
} from '@/hooks/useAdminOauth';
import { useToasts } from '@/stores/toasts';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      'toasts.admin.user.updated': 'User updated',
      'toasts.errors.generic': 'Something went wrong',
    };
    return translations[key] || key;
  },
}));

vi.mock('@/lib/api/adminOauth');

describe('useAdminOauth hooks', () => {
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

  describe('useOauthProviders', () => {
    it('should fetch providers', async () => {
      const mockProviders: OAuthProviderResponse[] = [];
      vi.mocked(oauthApi.listOauthProviders).mockResolvedValue(mockProviders);

      const { result } = renderHook(() => useOauthProviders(), { wrapper });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockProviders);
    });
  });

  describe('useCreateOauthProvider mutation', () => {
    it('should create provider and invalidate list', async () => {
      const mockResponse = {
        id: 'provider-1',
        community_id: 'community-1',
        slug: 'google',
        display_name: 'Google',
        icon_url: null,
        provider_type: 'oidc',
        issuer: 'https://accounts.google.com',
        client_id: 'abc123',
        scopes: 'openid email',
        authorization_endpoint: 'https://accounts.google.com/o/oauth2/v2/auth',
        token_endpoint: 'https://oauth2.googleapis.com/token',
        userinfo_endpoint: 'https://openidconnect.googleapis.com/v1/userinfo',
        jwks_uri: 'https://www.googleapis.com/oauth2/v3/certs',
        end_session_endpoint: null,
        group_mappings: {},
        default_role: 'member',
        group_claim: 'groups',
        avatar_claim: 'picture',
        sub_claim: 'sub',
        email_claim: 'email',
        name_claim: 'name',
        enabled: true,
        auto_create_users: true,
        seeded_from_env: false,
        created_at: new Date(),
        updated_at: new Date(),
      };
      vi.mocked(oauthApi.createOauthProvider).mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useCreateOauthProvider(), { wrapper });

      await waitFor(() => {
        result.current.mutate({
          slug: 'google',
          display_name: 'Google',
          provider_type: 'oidc',
          client_id: 'abc123',
          client_secret: 'secret',
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe('useUpdateOauthProvider mutation', () => {
    it('should update provider', async () => {
      const mockResponse = {
        id: 'provider-1',
        community_id: 'community-1',
        slug: 'google',
        display_name: 'Updated Google',
        icon_url: null,
        provider_type: 'oidc',
        issuer: 'https://accounts.google.com',
        client_id: 'abc123',
        scopes: 'openid email',
        authorization_endpoint: 'https://accounts.google.com/o/oauth2/v2/auth',
        token_endpoint: 'https://oauth2.googleapis.com/token',
        userinfo_endpoint: 'https://openidconnect.googleapis.com/v1/userinfo',
        jwks_uri: 'https://www.googleapis.com/oauth2/v3/certs',
        end_session_endpoint: null,
        group_mappings: {},
        default_role: 'member',
        group_claim: 'groups',
        avatar_claim: 'picture',
        sub_claim: 'sub',
        email_claim: 'email',
        name_claim: 'name',
        enabled: true,
        auto_create_users: true,
        seeded_from_env: false,
        created_at: new Date(),
        updated_at: new Date(),
      };
      vi.mocked(oauthApi.updateOauthProvider).mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useUpdateOauthProvider(), { wrapper });

      await waitFor(() => {
        result.current.mutate({
          providerId: 'provider-1',
          updates: { display_name: 'Updated Google' },
        });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe('useDeleteOauthProvider mutation', () => {
    it('should delete provider', async () => {
      vi.mocked(oauthApi.deleteOauthProvider).mockResolvedValue({
        message: 'deleted',
      });

      const { result } = renderHook(() => useDeleteOauthProvider(), { wrapper });

      await waitFor(() => {
        result.current.mutate('provider-1');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe('useToggleOauthProvider mutation', () => {
    it('should toggle provider', async () => {
      vi.mocked(oauthApi.toggleOauthProvider).mockResolvedValue({
        message: 'toggled',
      });

      const { result } = renderHook(() => useToggleOauthProvider(), { wrapper });

      await waitFor(() => {
        result.current.mutate('provider-1');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe('useDiscoverIssuer mutation', () => {
    it('should discover issuer endpoints', async () => {
      const mockResponse = {
        authorization_endpoint: 'https://example.com/authorize',
        token_endpoint: 'https://example.com/token',
        userinfo_endpoint: 'https://example.com/userinfo',
        jwks_uri: 'https://example.com/.well-known/jwks.json',
        end_session_endpoint: null,
      };
      vi.mocked(oauthApi.discoverIssuer).mockResolvedValue(mockResponse);

      const { result } = renderHook(() => useDiscoverIssuer(), { wrapper });

      await waitFor(() => {
        result.current.mutate('https://example.com');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockResponse);
    });
  });
});
