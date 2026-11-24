/**
 * @file tests/unit/auth/oauthCallback.test.tsx
 * @brief OAuth callback: tokens -> /app; first link needing 2FA -> two-factor page.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { waitFor } from "@testing-library/react";
import { renderWithProviders as render } from "../../utils/renderWithProviders";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams("code=abc"),
}));
vi.mock("@/lib/api/auth", () => ({ oauthExchange: vi.fn() }));
vi.mock("@/lib/auth/flow", () => ({
  completeLogin: vi.fn(),
  twoFactorUrl: (n: string) => `/two-factor?next=${encodeURIComponent(n)}`,
}));

import OAuthCallbackPage from "@/app/(auth)/callback/page";
import * as api from "@/lib/api/auth";
import * as flow from "@/lib/auth/flow";

beforeEach(() => vi.clearAllMocks());

describe("OAuthCallbackPage", () => {
  it("lands on /app when tokens are issued", async () => {
    vi.mocked(api.oauthExchange).mockResolvedValue({} as never);
    vi.mocked(flow.completeLogin).mockResolvedValue({ kind: "authenticated" });
    render(<OAuthCallbackPage />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"));
    expect(api.oauthExchange).toHaveBeenCalledWith("abc");
  });

  it("routes to the two-factor page when 2FA is pending", async () => {
    vi.mocked(api.oauthExchange).mockResolvedValue({} as never);
    vi.mocked(flow.completeLogin).mockResolvedValue({
      kind: "two_factor",
      two_factor_token: "p",
      methods: ["totp"],
    });
    render(<OAuthCallbackPage />);
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/two-factor?next=%2Fapp"),
    );
  });
});
