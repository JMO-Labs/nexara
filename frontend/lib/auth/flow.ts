/**
 * @file lib/auth/flow.ts
 * @brief Helpers that complete an auth flow: store the access token, hydrate
 *        the session store with /users/me, and surface 2FA continuation.
 */
import { clearUserCache } from "@/lib/pwa/clearUserCache";
import { setAccessToken } from "./session";
import type { LoginResponse } from "@/lib/api/auth";
import { getMe } from "@/lib/api/users";
import { useSession } from "@/stores/session";
import { usePendingTwoFactor } from "@/stores/pendingTwoFactor";

export type AuthOutcome =
  | { kind: "authenticated" }
  | { kind: "two_factor"; two_factor_token: string; methods: string[] };

/**
 * @brief URL of the two-factor page (token and methods live in memory).
 * @param next post-login destination
 * @return relative URL
 */
export const twoFactorUrl = (next: string): string =>
  `/two-factor?next=${encodeURIComponent(next)}`;

export async function completeLogin(resp: LoginResponse): Promise<AuthOutcome> {
  if (resp.requires_2fa && resp.two_factor_token) {
    const methods = resp.two_factor_methods?.length
      ? resp.two_factor_methods
      : ["totp", "recovery"];
    usePendingTwoFactor.getState().set(resp.two_factor_token, methods);
    return {
      kind: "two_factor",
      two_factor_token: resp.two_factor_token,
      methods,
    };
  }
  if (!resp.access_token) {
    throw new Error("Authentication response missing access token.");
  }
  usePendingTwoFactor.getState().clear();
  setAccessToken(resp.access_token);
  const user = await getMe();
  clearUserCache();
  useSession.getState().setUser(user);
  return { kind: "authenticated" };
}
