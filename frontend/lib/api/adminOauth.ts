/**
 * @file lib/api/adminOauth.ts
 * @brief OAuth provider management API endpoints for admin panel.
 */
import { apiGet, apiPost, apiPut, apiPatch, apiDelete, seg } from "./client";

/**
 * @brief OAuth provider response (excludes client_secret).
 */
export interface OAuthProviderResponse {
  id: string;
  community_id: string;
  slug: string;
  display_name: string;
  icon_url: string | null;
  provider_type: string;
  issuer: string | null;
  client_id: string;
  scopes: string;
  authorization_endpoint: string | null;
  token_endpoint: string | null;
  userinfo_endpoint: string | null;
  jwks_uri: string | null;
  end_session_endpoint: string | null;
  group_mappings: Record<string, string>;
  default_role: string;
  group_claim: string;
  avatar_claim: string;
  sub_claim: string;
  email_claim: string;
  name_claim: string;
  enabled: boolean;
  auto_create_users: boolean;
  seeded_from_env: boolean;
  created_at: Date;
  updated_at: Date;
}

/**
 * @brief OAuth provider creation payload.
 */
export interface OAuthProviderCreate {
  slug: string;
  display_name: string;
  provider_type: string;
  client_id: string;
  client_secret: string;
  issuer?: string;
  icon_url?: string;
  scopes?: string;
  authorization_endpoint?: string;
  token_endpoint?: string;
  userinfo_endpoint?: string;
  jwks_uri?: string;
  end_session_endpoint?: string;
  group_mappings?: Record<string, string>;
  default_role?: string;
  group_claim?: string;
  avatar_claim?: string;
  sub_claim?: string;
  email_claim?: string;
  name_claim?: string;
  enabled?: boolean;
  auto_create_users?: boolean;
}

/**
 * @brief OAuth provider update payload (all fields optional).
 */
export interface OAuthProviderUpdate {
  slug?: string;
  display_name?: string;
  provider_type?: string;
  client_id?: string;
  client_secret?: string;
  issuer?: string;
  icon_url?: string;
  scopes?: string;
  authorization_endpoint?: string;
  token_endpoint?: string;
  userinfo_endpoint?: string;
  jwks_uri?: string;
  end_session_endpoint?: string;
  group_mappings?: Record<string, string>;
  default_role?: string;
  group_claim?: string;
  avatar_claim?: string;
  sub_claim?: string;
  email_claim?: string;
  name_claim?: string;
  enabled?: boolean;
  auto_create_users?: boolean;
}

/**
 * @brief OIDC discovery response.
 */
export interface IssuerDiscoveryResponse {
  authorization_endpoint: string;
  token_endpoint: string;
  userinfo_endpoint: string;
  jwks_uri: string;
  end_session_endpoint: string | null;
}

/**
 * @brief Message response.
 */
export interface MessageResponse {
  message: string;
}

/**
 * @brief List all OAuth providers.
 * @return Array of OAuthProviderResponse
 */
export const listOauthProviders = () =>
  apiGet<OAuthProviderResponse[]>("/api/v1/admin/oauth/providers");

/**
 * @brief Create a new OAuth provider.
 * @param payload Provider creation data
 * @return OAuthProviderResponse
 */
export const createOauthProvider = (payload: OAuthProviderCreate) =>
  apiPost<OAuthProviderResponse>("/api/v1/admin/oauth/providers", payload);

/**
 * @brief Update an OAuth provider.
 * @param providerId Provider ID
 * @param updates Partial update payload
 * @return OAuthProviderResponse
 */
export const updateOauthProvider = (
  providerId: string,
  updates: OAuthProviderUpdate,
) =>
  apiPut<OAuthProviderResponse>(
    `/api/v1/admin/oauth/providers/${seg(providerId)}`,
    updates,
  );

/**
 * @brief Delete an OAuth provider.
 * @param providerId Provider ID
 * @return MessageResponse
 */
export const deleteOauthProvider = (providerId: string) =>
  apiDelete<MessageResponse>(
    `/api/v1/admin/oauth/providers/${seg(providerId)}`,
  );

/**
 * @brief Toggle OAuth provider enabled/disabled status.
 * @param providerId Provider ID
 * @return MessageResponse
 */
export const toggleOauthProvider = (providerId: string) =>
  apiPost<MessageResponse>(
    `/api/v1/admin/oauth/providers/${seg(providerId)}/toggle`,
  );

/**
 * @brief Discover OAuth endpoints from issuer URL.
 * @param issuer OIDC issuer URL
 * @return IssuerDiscoveryResponse with discovered endpoints
 */
export const discoverIssuer = (issuer: string) =>
  apiPost<IssuerDiscoveryResponse>("/api/v1/admin/oauth/discover", { issuer });

/**
 * @brief Enable/disable SSO-only login enforcement.
 * @param enabled New state
 * @return new state plus optional lockout warning
 */
export const setSsoOnly = (enabled: boolean) =>
  apiPatch<{ sso_only: boolean; warning: string | null }>(
    "/api/v1/admin/settings/sso-only",
    { enabled },
  );
