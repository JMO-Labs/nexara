/**
 * @file tests/middleware/auth.test.ts
 * @brief TDD tests for the global auth route guard middleware.
 *
 * Verifies that unauthenticated users are redirected to login for
 * protected routes, authenticated users pass through, and public
 * routes are accessible without auth.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "~/stores/auth";
import { authMiddleware } from "~/middleware/auth.global";

/** @brief Helper to create a minimal route-like object. */
function makeRoute(path: string) {
  return { path, fullPath: path, params: {}, query: {}, name: "" };
}

describe("auth middleware", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it("redirects unauthenticated users to /auth/login for /app routes", () => {
    const to = makeRoute("/app/feed");
    const from = makeRoute("/");

    const result = authMiddleware(to, from);

    expect(result).toEqual({
      path: "/auth/login",
      query: { redirect: "/app/feed" },
    });
  });

  it("redirects unauthenticated users for nested /app routes", () => {
    const to = makeRoute("/app/post/123");
    const from = makeRoute("/");

    const result = authMiddleware(to, from);

    expect(result).toEqual({
      path: "/auth/login",
      query: { redirect: "/app/post/123" },
    });
  });

  it("allows authenticated users through to /app routes", () => {
    const authStore = useAuthStore();
    authStore.accessToken = "valid-token";
    authStore.user = {
      id: "1",
      email: "a@b.com",
      username: "a",
      display_name: "A",
      email_verified: true,
      avatar_url: null,
      bio: null,
      pronouns: null,
      location: null,
      website_url: null,
      birthday: null,
      role: "member",
      totp_enabled: false,
      storage_used: 0,
      storage_quota: 1073741824,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      last_seen_at: null,
    };

    const to = makeRoute("/app/feed");
    const from = makeRoute("/");

    const result = authMiddleware(to, from);

    expect(result).toBeUndefined();
  });

  it("allows access to the landing page without auth", () => {
    const to = makeRoute("/");
    const from = makeRoute("/");

    const result = authMiddleware(to, from);

    expect(result).toBeUndefined();
  });

  it("allows access to /auth/* routes without auth", () => {
    const routes = [
      "/auth/login",
      "/auth/register",
      "/auth/reset-password",
      "/auth/two-factor",
    ];
    for (const path of routes) {
      const to = makeRoute(path);
      const from = makeRoute("/");
      const result = authMiddleware(to, from);
      expect(result).toBeUndefined();
    }
  });

  it("redirects authenticated users from /auth/* to /app", () => {
    const authStore = useAuthStore();
    authStore.accessToken = "valid-token";
    authStore.user = {
      id: "1",
      email: "a@b.com",
      username: "a",
      display_name: "A",
      email_verified: true,
      avatar_url: null,
      bio: null,
      pronouns: null,
      location: null,
      website_url: null,
      birthday: null,
      role: "member",
      totp_enabled: false,
      storage_used: 0,
      storage_quota: 1073741824,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      last_seen_at: null,
    };

    const to = makeRoute("/auth/login");
    const from = makeRoute("/");

    const result = authMiddleware(to, from);

    expect(result).toEqual({ path: "/app" });
  });
});
