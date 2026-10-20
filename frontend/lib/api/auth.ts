/**
 * @file lib/api/auth.ts
 * @brief Auth endpoint wrappers. All flows return LoginResponse-shaped data
 *        when a session is established; cookie is set by the backend.
 */
import { apiPost, apiGet } from "./client";

export interface LoginResponse {
  access_token: string | null;
  token_type: string;
  expires_in: number | null;
  requires_2fa: boolean;
  two_factor_token: string | null;
}

export interface MessageResponse {
  message: string;
}

export interface OAuthProvider {
  slug: string;
  display_name: string;
  icon_url: string | null;
}

export interface AuthConfig {
  oidc_enabled: boolean;
  registration_enabled: boolean;
  local_auth_enabled: boolean;
  oauth_providers: OAuthProvider[];
}

export interface LogoutResponse {
  message: string;
  end_session_url: string | null;
}

const AUTH = "/api/v1/auth";

export const getAuthConfig = () =>
  apiGet<AuthConfig>(`${AUTH}/config`, { anonymous: true });

export const login = (email: string, password: string) =>
  apiPost<LoginResponse>(
    `${AUTH}/login`,
    { email, password },
    { anonymous: true },
  );

export const register = (body: {
  email: string;
  username: string;
  password: string;
  display_name: string;
  invite_token?: string;
}) => apiPost<LoginResponse>(`${AUTH}/register`, body, { anonymous: true });

export const logout = () => apiPost<LogoutResponse>(`${AUTH}/logout`);

export const verifyTwoFactorLogin = (two_factor_token: string, code: string) =>
  apiPost<LoginResponse>(
    `${AUTH}/2fa/login`,
    { two_factor_token, code },
    { anonymous: true },
  );

export const enrollTwoFactor = () =>
  apiPost<{ secret: string; otpauth_uri: string }>(`${AUTH}/2fa/enroll`);

export const verifyTwoFactorEnroll = (code: string) =>
  apiPost<{ backup_codes: string[] }>(`${AUTH}/2fa/verify`, { code });

export const requestMagicLink = (email: string) =>
  apiPost<MessageResponse>(
    `${AUTH}/magic-link/request`,
    { email },
    { anonymous: true },
  );

export const verifyMagicLink = (token: string) =>
  apiGet<LoginResponse>(
    `${AUTH}/magic-link/verify?token=${encodeURIComponent(token)}`,
    { anonymous: true },
  );

export const requestPasswordReset = (email: string) =>
  apiPost<MessageResponse>(
    `${AUTH}/password-reset/request`,
    { email },
    { anonymous: true },
  );

export const confirmPasswordReset = (token: string, new_password: string) =>
  apiPost<MessageResponse>(
    `${AUTH}/password-reset/confirm`,
    { token, new_password },
    { anonymous: true },
  );

export const oauthExchange = (code: string) =>
  apiPost<LoginResponse>(
    "/api/v1/oauth/exchange",
    { code },
    { anonymous: true },
  );

/** URL the browser should hit to start an OAuth flow. */
export const oauthLoginUrl = (slug: string, apiBase: string) =>
  `${apiBase}/api/v1/oauth/${encodeURIComponent(slug)}/login`;
