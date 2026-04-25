/**
 * @file tests/unit/admin/adminOauthApi.test.ts
 * @brief Tests for OAuth provider admin API functions.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '@/lib/api/client';
import {
  listOauthProviders,
  createOauthProvider,
  updateOauthProvider,
  deleteOauthProvider,
  toggleOauthProvider,
  discoverIssuer,
} from '@/lib/api/adminOauth';

vi.mock('@/lib/api/client');

describe('adminOauthApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listOauthProviders', () => {
    it('should call apiGet with correct path', async () => {
      const mockProviders = [
        {
          id: 'provider-1',
          community_id: 'community-1',
          slug: 'google',
          display_name: 'Google',
          icon_url: null,
          provider_type: 'oidc',
          issuer: 'https://accounts.google.com',
          client_id: 'abc123',
          scopes: 'openid email profile',
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
        },
      ];
      vi.mocked(client.apiGet).mockResolvedValue(mockProviders);

      const result = await listOauthProviders();

      expect(client.apiGet).toHaveBeenCalledWith('/api/v1/admin/oauth/providers');
      expect(result).toEqual(mockProviders);
    });
  });

  describe('createOauthProvider', () => {
    it('should call apiPost with provider data', async () => {
      const mockResponse = {
        id: 'provider-1',
        community_id: 'community-1',
        slug: 'custom',
        display_name: 'Custom Provider',
        icon_url: null,
        provider_type: 'oidc',
        issuer: 'https://example.com',
        client_id: 'abc123',
        scopes: 'openid email',
        authorization_endpoint: 'https://example.com/authorize',
        token_endpoint: 'https://example.com/token',
        userinfo_endpoint: 'https://example.com/userinfo',
        jwks_uri: 'https://example.com/.well-known/jwks.json',
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
      vi.mocked(client.apiPost).mockResolvedValue(mockResponse);

      const payload = {
        slug: 'custom',
        display_name: 'Custom Provider',
        provider_type: 'oidc',
        client_id: 'abc123',
        client_secret: 'secret123',
        issuer: 'https://example.com',
      };

      const result = await createOauthProvider(payload);

      expect(client.apiPost).toHaveBeenCalledWith(
        '/api/v1/admin/oauth/providers',
        payload,
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('updateOauthProvider', () => {
    it('should call apiPut with provider id and updates', async () => {
      const mockResponse = {
        id: 'provider-1',
        community_id: 'community-1',
        slug: 'custom',
        display_name: 'Updated Name',
        icon_url: null,
        provider_type: 'oidc',
        issuer: 'https://example.com',
        client_id: 'abc123',
        scopes: 'openid email',
        authorization_endpoint: 'https://example.com/authorize',
        token_endpoint: 'https://example.com/token',
        userinfo_endpoint: 'https://example.com/userinfo',
        jwks_uri: 'https://example.com/.well-known/jwks.json',
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
      vi.mocked(client.apiPut).mockResolvedValue(mockResponse);

      const result = await updateOauthProvider('provider-1', {
        display_name: 'Updated Name',
      });

      expect(client.apiPut).toHaveBeenCalledWith(
        '/api/v1/admin/oauth/providers/provider-1',
        { display_name: 'Updated Name' },
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('deleteOauthProvider', () => {
    it('should call apiDelete with provider id', async () => {
      const mockResponse = { message: 'Provider deleted' };
      vi.mocked(client.apiDelete).mockResolvedValue(mockResponse);

      const result = await deleteOauthProvider('provider-1');

      expect(client.apiDelete).toHaveBeenCalledWith(
        '/api/v1/admin/oauth/providers/provider-1',
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('toggleOauthProvider', () => {
    it('should call apiPost with provider id', async () => {
      const mockResponse = { message: 'Provider toggled' };
      vi.mocked(client.apiPost).mockResolvedValue(mockResponse);

      const result = await toggleOauthProvider('provider-1');

      expect(client.apiPost).toHaveBeenCalledWith(
        '/api/v1/admin/oauth/providers/provider-1/toggle',
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('discoverIssuer', () => {
    it('should call apiPost with issuer url', async () => {
      const mockResponse = {
        authorization_endpoint: 'https://example.com/authorize',
        token_endpoint: 'https://example.com/token',
        userinfo_endpoint: 'https://example.com/userinfo',
        jwks_uri: 'https://example.com/.well-known/jwks.json',
        end_session_endpoint: null,
      };
      vi.mocked(client.apiPost).mockResolvedValue(mockResponse);

      const result = await discoverIssuer('https://example.com');

      expect(client.apiPost).toHaveBeenCalledWith(
        '/api/v1/admin/oauth/discover',
        { issuer: 'https://example.com' },
      );
      expect(result).toEqual(mockResponse);
    });
  });
});
