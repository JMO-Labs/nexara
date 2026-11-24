/**
 * @file lib/auth/flow.ts
 * @brief Helpers that complete an auth flow: store the access token, hydrate
 *        the session store with /users/me, and surface 2FA continuation.
 */
import { setAccessToken } from "./session";
import type { LoginResponse } from "@/lib/api/auth";
import { getMe } from "@/lib/api/users";
import { useSession } from "@/stores/session";

export type AuthOutcome =
  | { kind: "authenticated" }
  | { kind: "two_factor"; two_factor_token: string; methods: string[] };

/**
 * @brief URL of the two-factor page for a pending login.
 * @param out two_factor outcome
 * @param next post-login destination
 * @return relative URL
 */
export function twoFactorUrl(
  out: Extract<AuthOutcome, { kind: "two_factor" }>,
  next: string,
): string {
  const m = encodeURIComponent(out.methods.join(","));
  return `/two-factor?token=${encodeURIComponent(out.two_factor_token)}&methods=${m}&next=${encodeURIComponent(next)}`;
}

export async function completeLogin(resp: LoginResponse): Promise<AuthOutcome> {
  if (resp.requires_2fa && resp.two_factor_token) {
    return {
      kind: "two_factor",
      two_factor_token: resp.two_factor_token,
      methods: resp.two_factor_methods?.length
        ? resp.two_factor_methods
        : ["totp", "recovery"],
    };
  }
  if (!resp.access_token) {
    throw new Error("Authentication response missing access token.");
  }
  setAccessToken(resp.access_token);
  const user = await getMe();
  useSession.getState().setUser(user);
  return { kind: "authenticated" };
}
