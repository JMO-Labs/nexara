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
  discovery_url: string | null;
  claim_mapping: ClaimMapping;
  client_id: string;
  scopes: string;
  authorization_endpoint: string | null;
  token_endpoint: string | null;
  userinfo_endpoint: string | null;
  jwks_uri: string | null;
  end_session_endpoint: string | null;
  group_mappings: Record<string, string>;
  default_role: string;
  preset: string | null;
  allowed_domains: string[];
  required_group: string | null;
  username_claim: string;
  sync_profile: boolean;
  trust_email: boolean;
  enabled: boolean;
  auto_create_users: boolean;
  seeded_from_env: boolean;
  created_at: Date;
  updated_at: Date;
  /** Redirect URI to register at the IdP (computed by the backend). */
  callback_url: string;
}

/** @brief One IdP group rule: community role (no subgroup_id) or subgroup membership. */
export interface GroupRule {
  subgroup_id: string | null;
  role: string;
}

/** @brief claim_mapping: string claim overrides plus optional group_mapping. */
export interface ClaimMapping {
  group_mapping?: Record<string, GroupRule | GroupRule[]>;
  [claim: string]: string | Record<string, GroupRule | GroupRule[]> | undefined;
}

/** @brief Built-in provider preset (GET /admin/oauth/presets). */
export interface OAuthPreset {
  key: string;
  kind: "oidc" | "oauth2";
  label: string;
  scopes: string;
  help: string;
  discovery_url: string | null;
  params: string[];
  defaults: Record<string, string>;
  authorization_endpoint: string | null;
  token_endpoint: string | null;
  userinfo_endpoint: string | null;
  claim_mapping: Record<string, string>;
  username_claim: string;
  /** Default for the provider's trust_email. */
  trust_email: boolean;
}

/** @brief postMessage type the /sso-test popup sends to its opener. */
export const SSO_TEST_MESSAGE = "nexara:sso-test";

/** @brief What a real sign-in would do for the tested identity. */
export interface TestLoginOutcome {
  allowed: boolean;
  action: "sign_in" | "link" | "link_after_2fa" | "create" | null;
  code: string | null;
}

/** @brief Admin test-login report (nothing was provisioned). */
export interface TestLoginResult {
  provider_id: string;
  claims: Record<string, unknown>;
  identity: {
    sub: string;
    email: string | null;
    email_verified: boolean;
    display_name: string | null;
    username: string | null;
    groups: string[];
  };
  role: string;
  role_mapped: boolean;
  subgroups: { id: string; name: string; role: string }[];
  outcome: TestLoginOutcome;
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
  discovery_url?: string;
  claim_mapping?: ClaimMapping;
  icon_url?: string;
  scopes?: string;
  authorization_endpoint?: string;
  token_endpoint?: string;
  userinfo_endpoint?: string;
  jwks_uri?: string;
  end_session_endpoint?: string;
  group_mappings?: Record<string, string>;
  default_role?: string;
  preset?: string;
  allowed_domains?: string[];
  required_group?: string | null;
  username_claim?: string;
  sync_profile?: boolean;
  trust_email?: boolean;
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
  discovery_url?: string;
  claim_mapping?: ClaimMapping;
  icon_url?: string;
  scopes?: string;
  authorization_endpoint?: string;
  token_endpoint?: string;
  userinfo_endpoint?: string;
  jwks_uri?: string;
  end_session_endpoint?: string;
  group_mappings?: Record<string, string>;
  default_role?: string;
  preset?: string;
  allowed_domains?: string[];
  required_group?: string | null;
  username_claim?: string;
  sync_profile?: boolean;
  trust_email?: boolean;
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

/**
 * @brief List built-in provider presets.
 * @return presets
 */
export const listOauthPresets = () =>
  apiGet<OAuthPreset[]>("/api/v1/admin/oauth/presets");

/**
 * @brief Redirect URI template for unsaved providers ("{slug}" placeholder).
 * @return template
 */
export const getCallbackTemplate = () =>
  apiGet<{ template: string }>("/api/v1/admin/oauth/callback-url");

/**
 * @brief Start an admin test login (nothing is provisioned).
 * @param providerId Provider ID
 * @return IdP authorize URL for the popup
 */
export const startTestLogin = (providerId: string) =>
  apiPost<{ authorize_url: string }>(
    `/api/v1/admin/oauth/providers/${seg(providerId)}/test-login`,
  );

/**
 * @brief One-time read of a test-login result.
 * @param resultId id posted back by the popup
 * @return test result
 */
export const readTestLogin = (resultId: string) =>
  apiGet<TestLoginResult>(`/api/v1/admin/oauth/test-login/${seg(resultId)}`);
