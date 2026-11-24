/**
 * @file lib/passkeys.ts
 * @brief Browser WebAuthn ceremonies glued to the passkey API.
 */
import {
  startAuthentication,
  startRegistration,
} from "@simplewebauthn/browser";
import type { LoginResponse } from "@/lib/api/auth";
import * as api from "@/lib/api/twoFactor";
import { refreshAccessToken } from "@/lib/auth/session";

/** @brief True when the page can use WebAuthn (HTTPS or localhost). */
export const passkeysAvailable = (): boolean =>
  typeof window !== "undefined" && window.isSecureContext === true;

/**
 * @brief Register a passkey for the signed-in user, then refresh claims.
 * @param name display name
 * @return stored passkey
 */
export async function registerPasskey(name: string) {
  const options = await api.passkeyRegisterOptions();
  const credential = await startRegistration({
    optionsJSON: options as unknown as Parameters<
      typeof startRegistration
    >[0]["optionsJSON"],
  });
  const saved = await api.passkeyRegisterVerify(credential, name);
  await refreshAccessToken();
  return saved;
}

/**
 * @brief Authenticate with a passkey (sign-in, or the 2FA step).
 * @param opts optional email hint and pending 2FA token
 * @return login response from the server
 */
export async function authenticateWithPasskey(
  opts: { email?: string; pendingToken?: string } = {},
): Promise<LoginResponse> {
  const options = await api.passkeyLoginOptions(opts.email);
  const credential = await startAuthentication({
    optionsJSON: options as unknown as Parameters<
      typeof startAuthentication
    >[0]["optionsJSON"],
  });
  return api.passkeyLoginVerify(credential, opts.pendingToken);
}
