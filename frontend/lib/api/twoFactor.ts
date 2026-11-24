/**
 * @file lib/api/twoFactor.ts
 * @brief Wrappers for /auth/2fa, /auth/passkeys and the admin 2FA policy.
 */
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, seg } from "./client";
import type { LoginResponse, MessageResponse } from "./auth";

const TFA = "/api/v1/auth/2fa";
const PK = "/api/v1/auth/passkeys";

export interface TwoFactorStatus {
  totp: boolean;
  passkeys: number;
  recovery_left: number;
  required: boolean;
  grace_until: string | null;
}

export interface PasskeyInfo {
  id: string;
  name: string;
  transports: string[];
  created_at: string;
  last_used_at: string | null;
}

export type Require2fa = "off" | "admins" | "everyone";

export const getTwoFactorStatus = () =>
  apiGet<TwoFactorStatus>(`${TFA}/status`);

export const totpStart = () =>
  apiPost<{ otpauth_uri: string; secret: string }>(`${TFA}/totp/start`);

export const totpConfirm = (code: string) =>
  apiPost<{ recovery_codes: string[] }>(`${TFA}/totp/confirm`, { code });

export const totpDisable = (proof: { password?: string; code?: string }) =>
  apiPost<MessageResponse>(`${TFA}/totp/disable`, proof);

export const regenerateRecovery = (code: string) =>
  apiPost<{ recovery_codes: string[] }>(`${TFA}/recovery/regenerate`, {
    code,
  });

export const listPasskeys = () => apiGet<PasskeyInfo[]>(PK);

export const renamePasskey = (id: string, name: string) =>
  apiPatch<PasskeyInfo>(`${PK}/${seg(id)}`, { name });

export const deletePasskey = (id: string) =>
  apiDelete<MessageResponse>(`${PK}/${seg(id)}`);

export const passkeyRegisterOptions = () =>
  apiPost<Record<string, unknown>>(`${PK}/register/options`);

export const passkeyRegisterVerify = (credential: unknown, name: string) =>
  apiPost<PasskeyInfo>(`${PK}/register/verify`, { credential, name });

export const passkeyLoginOptions = (email?: string) =>
  apiPost<Record<string, unknown>>(
    `${PK}/login/options`,
    email ? { email } : {},
    { anonymous: true },
  );

export const passkeyLoginVerify = (
  credential: unknown,
  pending_token?: string,
) =>
  apiPost<LoginResponse>(
    `${PK}/login/verify`,
    pending_token ? { credential, pending_token } : { credential },
    { anonymous: true },
  );

export const resetUserTwoFactor = (userId: string) =>
  apiPost<MessageResponse>(`/api/v1/admin/users/${seg(userId)}/reset-2fa`);

export const getSecurityPolicy = () =>
  apiGet<{ require_2fa: Require2fa }>("/api/v1/admin/security");

export const putSecurityPolicy = (require_2fa: Require2fa) =>
  apiPut<{ require_2fa: Require2fa }>("/api/v1/admin/security", {
    require_2fa,
  });
