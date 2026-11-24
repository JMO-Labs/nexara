/**
 * @file lib/auth/session.ts
 * @brief Access-token store (memory) + refresh primitive. Refresh token is
 *        an HttpOnly cookie issued by backend at /api/v1/auth — never
 *        readable from JS, so all we track here is the short-lived access JWT.
 *        SSR-safe: zero browser globals at module top level.
 */
import { ApiError } from "@/lib/api/errors";
import { usePendingTwoFactor } from "@/stores/pendingTwoFactor";

let accessToken: string | null = null;
const listeners = new Set<(token: string | null) => void>();

/** Non-sensitive cookie used by the edge proxy to soft-gate /app vs /login.
 *  The real refresh token is HttpOnly and scoped to /api/v1/auth, so it is
 *  invisible to the Next.js edge runtime. This hint cookie is set/cleared
 *  client-side only; the backend never reads it. */
const HINT_COOKIE = "nx_session";

function setHintCookie(active: boolean): void {
  if (typeof document === "undefined") return;
  if (active) {
    document.cookie = `${HINT_COOKIE}=1; Path=/; SameSite=Lax; Max-Age=2592000`;
  } else {
    document.cookie = `${HINT_COOKIE}=; Path=/; SameSite=Lax; Max-Age=0`;
  }
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
  setHintCookie(!!token);
  for (const l of listeners) l(token);
}

export function onAuthChange(fn: (token: string | null) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** Empty string = same-origin requests (Next rewrites in next.config.ts
 *  forward `/api/*` to the FastAPI backend). Override with
 *  NEXT_PUBLIC_API_BASE_URL only if pointing at a remote API directly. */
export const API_BASE: string = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/** Outcome of a refresh attempt. `transient` = network/server trouble, so the
 *  session was left untouched (only a 401/403 answer ends a session). */
export interface RefreshResult {
  token: string | null;
  transient: boolean;
}

let refreshPromise: Promise<RefreshResult> | null = null;

/**
 * @brief Exchange the HttpOnly refresh cookie for a new access token.
 *        De-duplicated: concurrent 401s share one in-flight refresh.
 *        Clears the session only on a 401/403 response; a network error,
 *        timeout or 5xx keeps it (offline must never sign the user out).
 * @return the new token, or null with `transient` telling why
 */
export async function refreshSession(): Promise<RefreshResult> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8_000);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        credentials: "include",
        signal: ctrl.signal,
      });
      if (res.status === 401 || res.status === 403) {
        setAccessToken(null);
        return { token: null, transient: false };
      }
      if (!res.ok) return { token: null, transient: true };
      const data = (await res.json()) as { access_token?: string };
      const next = data.access_token ?? null;
      setAccessToken(next);
      return { token: next, transient: false };
    } catch {
      return { token: null, transient: true };
    } finally {
      clearTimeout(timer);
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

/** @brief Token-only form of {@link refreshSession}; null on any failure. */
export async function refreshAccessToken(): Promise<string | null> {
  return (await refreshSession()).token;
}

/** @brief Unregister this device's push subscription (needs the token, so it
 *         runs before it is cleared). Best effort, capped at 3s. */
async function dropPushSubscription(): Promise<void> {
  const work = (async () => {
    const reg = await navigator.serviceWorker?.getRegistration();
    const sub = await reg?.pushManager?.getSubscription();
    if (!sub) return;
    const { unsubscribePush } = await import("@/lib/api/push");
    await unsubscribePush(sub.endpoint).catch(() => {});
    await sub.unsubscribe().catch(() => false);
  })().catch(() => {});
  let timer: ReturnType<typeof setTimeout> | undefined;
  await Promise.race([
    work,
    new Promise((r) => (timer = setTimeout(r, 3_000))),
  ]);
  clearTimeout(timer);
}

/** Best-effort logout: drops this device's push subscription, clears access
 *  token and any pending 2FA step, asks backend to revoke refresh cookie. */
export async function logout(): Promise<void> {
  if (typeof navigator !== "undefined") await dropPushSubscription();
  setAccessToken(null);
  usePendingTwoFactor.getState().clear();
  try {
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    /* network errors fine — local state is already cleared */
  }
}

/** Throws ApiError if no session can be established. */
export async function requireSession(): Promise<string> {
  const t = accessToken ?? (await refreshAccessToken());
  if (!t) throw new ApiError(401, "unauthenticated", "Sign in required.");
  return t;
}
