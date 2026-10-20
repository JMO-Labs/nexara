/**
 * @file tests/unit/auth-flow.test.ts
 * @brief completeLogin + auth-API smoke. Stubs fetch so the call shape is
 *        verified against the backend contract without a live server.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { completeLogin } from "@/lib/auth/flow";
import { useSession } from "@/stores/session";
import { setAccessToken, getAccessToken } from "@/lib/auth/session";
import * as authApi from "@/lib/api/auth";

describe("completeLogin", () => {
  beforeEach(() => {
    useSession.getState().reset();
    setAccessToken(null);
    vi.restoreAllMocks();
  });

  it("returns two_factor outcome when 2FA is required", async () => {
    const result = await completeLogin({
      access_token: null,
      token_type: "bearer",
      expires_in: null,
      requires_2fa: true,
      two_factor_token: "tft-123",
    });
    expect(result).toEqual({ kind: "two_factor", two_factor_token: "tft-123" });
    expect(getAccessToken()).toBeNull();
    expect(useSession.getState().user).toBeNull();
  });

  it("sets access token and hydrates user on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "u1",
            email: "a@b.com",
            username: "alice",
            display_name: "Alice",
            avatar_url: null,
            role: "member",
            is_active: true,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    const result = await completeLogin({
      access_token: "ax",
      token_type: "bearer",
      expires_in: 900,
      requires_2fa: false,
      two_factor_token: null,
    });

    expect(result).toEqual({ kind: "authenticated" });
    expect(getAccessToken()).toBe("ax");
    expect(useSession.getState().user?.username).toBe("alice");
    expect(useSession.getState().status).toBe("authenticated");
  });

  it("throws when neither access_token nor 2FA token is present", async () => {
    await expect(
      completeLogin({
        access_token: null,
        token_type: "bearer",
        expires_in: null,
        requires_2fa: false,
        two_factor_token: null,
      }),
    ).rejects.toThrow();
  });
});

describe("auth API", () => {
  beforeEach(() => {
    setAccessToken(null);
    vi.restoreAllMocks();
  });

  it("login posts to /api/v1/auth/login with email + password", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "a",
          token_type: "bearer",
          expires_in: 900,
          requires_2fa: false,
          two_factor_token: null,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await authApi.login("a@b.com", "pw");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/auth\/login$/);
    expect((init as RequestInit).method).toBe("POST");
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body).toEqual({ email: "a@b.com", password: "pw" });
    // anonymous flag should suppress the Authorization header
    const headers = (init as RequestInit).headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });
});
