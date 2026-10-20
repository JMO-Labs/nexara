/**
 * @file lib/auth/session.ts
 * @brief Access-token store (memory) + refresh primitive. Refresh token is
 *        an HttpOnly cookie issued by backend at /api/v1/auth — never
 *        readable from JS, so all we track here is the short-lived access JWT.
 *        SSR-safe: zero browser globals at module top level.
 */
import { ApiError } from "@/lib/api/errors";

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;
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

/**
 * Exchange the HttpOnly refresh cookie for a new access token.
 * De-duplicated: concurrent 401s share one in-flight refresh.
 */
export async function refreshAccessToken(): Promise<string | null> {
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
      if (!res.ok) {
        setAccessToken(null);
        return null;
      }
      const data = (await res.json()) as { access_token?: string };
      const next = data.access_token ?? null;
      setAccessToken(next);
      return next;
    } catch {
      setAccessToken(null);
      return null;
    } finally {
      clearTimeout(timer);
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

/** Best-effort logout: clears access token, asks backend to revoke refresh cookie. */
export async function logout(): Promise<void> {
  setAccessToken(null);
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
