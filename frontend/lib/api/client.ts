/**
 * @file lib/api/client.ts
 * @brief Typed fetch wrapper. Attaches Bearer access token, parses error
 *        envelope into ApiError, and on 401 transparently refreshes once.
 *        Mirrors retry semantics of frontend/composables/useApi.ts.
 */
import { ApiError } from "./errors";
import {
  API_BASE,
  getAccessToken,
  refreshAccessToken,
  setAccessToken,
} from "@/lib/auth/session";

export interface ApiOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Skip auth header even if a token is present. */
  anonymous?: boolean;
  /** Disable the 401-refresh-retry loop (used by the refresh call itself). */
  noRetry?: boolean;
  /** Abort timeout in ms. Default 30s. */
  timeoutMs?: number;
}

/** Encode one URL path segment; rejects empty and dot segments. */
export function seg(value: string | number): string {
  const v = String(value);
  if (v === "" || v === "." || v === "..")
    throw new Error(`Invalid path segment: "${v}"`);
  return encodeURIComponent(v);
}

function buildUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}

async function parseResponse<T>(res: Response): Promise<T> {
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

async function doFetch(path: string, opts: ApiOptions): Promise<Response> {
  const { body, anonymous, headers, timeoutMs = 30_000, ...rest } = opts;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const h = new Headers(headers);
  if (body !== undefined && !h.has("Content-Type"))
    h.set("Content-Type", "application/json");
  if (!anonymous) {
    const token = getAccessToken();
    if (token) h.set("Authorization", `Bearer ${token}`);
  }

  try {
    return await fetch(buildUrl(path), {
      ...rest,
      headers: h,
      credentials: "include",
      signal: controller.signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } finally {
    clearTimeout(timer);
  }
}

export async function api<T = unknown>(
  path: string,
  opts: ApiOptions = {},
): Promise<T> {
  let res = await doFetch(path, opts);

  if (res.status === 401 && !opts.noRetry && !opts.anonymous) {
    const next = await refreshAccessToken();
    if (next) {
      res = await doFetch(path, { ...opts, noRetry: true });
    } else {
      setAccessToken(null);
    }
  }

  // Persistent 401 after retry AND no token in memory → session is fully
  // gone. Notify listeners. Skip if a token has been re-set in the
  // meantime (stale in-flight requests after re-login should not kick).
  if (
    res.status === 401 &&
    !opts.anonymous &&
    getAccessToken() === null &&
    typeof window !== "undefined"
  ) {
    window.dispatchEvent(new CustomEvent("nx:auth-expired"));
  }

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* non-JSON error body */
    }
    throw ApiError.fromUnknown(res.status, body);
  }

  return parseResponse<T>(res);
}

/** Convenience verbs. */
export const apiGet = <T>(path: string, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "GET" });
export const apiPost = <T>(path: string, body?: unknown, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "POST", body });
export const apiPatch = <T>(path: string, body?: unknown, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "PATCH", body });
export const apiPut = <T>(path: string, body?: unknown, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "PUT", body });
export const apiDelete = <T = void>(path: string, opts?: ApiOptions) =>
  api<T>(path, { ...opts, method: "DELETE" });
