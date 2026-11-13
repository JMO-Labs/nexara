/**
 * @file tests/e2e/fixtures/api.ts
 * @brief Authenticated API helpers for e2e setup and cleanup. Logs in over
 *        HTTP (separate from the browser session) and returns a request
 *        context carrying the Bearer token.
 */
import { request, type APIRequestContext } from "@playwright/test";
import { E2E_EMAIL, E2E_PASSWORD } from "./auth";

const API_BASE =
  process.env.E2E_API_URL ??
  process.env.E2E_BASE_URL ??
  `http://localhost:${process.env.E2E_PORT ?? 3000}`;

/** @return unique suffix per run/worker, safe for slugs and titles */
export function uniqueId(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

/** @return API context authenticated as the e2e user */
export async function apiContext(): Promise<APIRequestContext> {
  const anon = await request.newContext({ baseURL: API_BASE });
  const res = await anon.post("/api/v1/auth/login", {
    data: { email: E2E_EMAIL, password: E2E_PASSWORD },
  });
  if (!res.ok()) throw new Error(`api login failed: ${res.status()}`);
  const { access_token } = (await res.json()) as { access_token: string };
  await anon.dispose();
  return request.newContext({
    baseURL: API_BASE,
    extraHTTPHeaders: { Authorization: `Bearer ${access_token}` },
  });
}
