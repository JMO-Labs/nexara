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
  | { kind: "two_factor"; two_factor_token: string };

export async function completeLogin(resp: LoginResponse): Promise<AuthOutcome> {
  if (resp.requires_2fa && resp.two_factor_token) {
    return { kind: "two_factor", two_factor_token: resp.two_factor_token };
  }
  if (!resp.access_token) {
    throw new Error("Authentication response missing access token.");
  }
  setAccessToken(resp.access_token);
  const user = await getMe();
  useSession.getState().setUser(user);
  return { kind: "authenticated" };
}
