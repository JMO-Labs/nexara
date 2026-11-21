/**
 * @file tests/unit/layout/useSignOut.test.tsx
 * @brief useSignOut clears auth, resets the session and redirects.
 */
import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";

const replace = vi.fn();
const logout = vi.fn();
const setAccessToken = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("@/lib/api/auth", () => ({
  logout: (...a: unknown[]) => logout(...a),
}));
vi.mock("@/lib/auth/session", () => ({
  setAccessToken: (...a: unknown[]) => setAccessToken(...a),
}));

import { useSession } from "@/stores/session";
import { useSignOut } from "@/hooks/useSignOut";

describe("useSignOut", () => {
  it("logs out, clears token and session, redirects", async () => {
    logout.mockResolvedValue(undefined);
    useSession.setState({
      user: { id: "u" } as never,
      status: "authenticated",
    });
    const { result } = renderHook(() => useSignOut());
    await result.current();
    expect(logout).toHaveBeenCalled();
    expect(setAccessToken).toHaveBeenCalledWith(null);
    expect(useSession.getState().user).toBeNull();
    expect(replace).toHaveBeenCalledWith("/login");
  });

  it("still signs out locally when the API fails", async () => {
    logout.mockRejectedValue(new Error("x"));
    replace.mockClear();
    const { result } = renderHook(() => useSignOut());
    await result.current();
    expect(replace).toHaveBeenCalledWith("/login");
  });
});
