/**
 * @file tests/integration/login-flow.test.ts
 * @brief Integration test for the login flow.
 *
 * Simulates the full login sequence: entering credentials, submitting
 * the form, storing the auth token, fetching the user profile, and
 * verifying the middleware allows navigation to the feed.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "~/stores/auth";
import { authMiddleware } from "~/middleware/auth.global";
import type { LoginResponse, User } from "~/types/api";

/** @brief User profile returned by GET /users/me. */
const mockUser: User = {
  id: "u1",
  email: "test@example.com",
  username: "testuser",
  display_name: "Test User",
  email_verified: true,
  avatar_url: null,
  bio: null,
  title: null,
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

/** @brief Backend login response (no user object). */
const mockLoginResponse: LoginResponse = {
  access_token: "integration-test-token",
  token_type: "bearer",
  expires_in: 1800,
  requires_2fa: false,
  two_factor_token: null,
};

/**
 * @brief Helper that mocks the two-step login flow: POST login + GET /users/me.
 */
function mockLoginFetches(): void {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(
      new Response(JSON.stringify(mockLoginResponse), { status: 200 }),
    )
    .mockResolvedValueOnce(
      new Response(JSON.stringify(mockUser), { status: 200 }),
    );
}

describe("login flow integration", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  it("complete login flow: credentials -> store -> middleware allows feed", async () => {
    const authStore = useAuthStore();

    const blocked = authMiddleware(
      { path: "/app", fullPath: "/app" },
      { path: "/auth/login" },
    );
    expect(blocked).toEqual({
      path: "/auth/login",
      query: { redirect: "/app" },
    });

    mockLoginFetches();
    await authStore.login({
      email: "test@example.com",
      password: "password123456",
    });

    expect(authStore.isAuthenticated).toBe(true);
    expect(authStore.user?.username).toBe("testuser");
    expect(authStore.accessToken).toBe("integration-test-token");

    const allowed = authMiddleware(
      { path: "/app", fullPath: "/app" },
      { path: "/auth/login" },
    );
    expect(allowed).toBeUndefined();
  });

  it("login with 2FA -> redirects to two-factor page", async () => {
    const authStore = useAuthStore();
    const twoFactorResponse: LoginResponse = {
      access_token: null,
      token_type: "bearer",
      expires_in: null,
      requires_2fa: true,
      two_factor_token: "2fa-tok",
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(twoFactorResponse), { status: 200 }),
    );
    await authStore.login({
      email: "test@example.com",
      password: "password123456",
    });

    expect(authStore.requiresTwoFactor).toBe(true);
    expect(authStore.isAuthenticated).toBe(false);
  });

  it("logout flow: clears state -> middleware blocks /app", async () => {
    const authStore = useAuthStore();

    mockLoginFetches();
    await authStore.login({
      email: "test@example.com",
      password: "password123456",
    });
    expect(authStore.isAuthenticated).toBe(true);

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(null, { status: 204 }),
    );
    await authStore.logout();

    expect(authStore.isAuthenticated).toBe(false);
    const blocked = authMiddleware(
      { path: "/app", fullPath: "/app" },
      { path: "/app" },
    );
    expect(blocked).toEqual({
      path: "/auth/login",
      query: { redirect: "/app" },
    });
  });
});
