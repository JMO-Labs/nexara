/**
 * @file tests/unit/auth/passkeyLogin.test.tsx
 * @brief Login passkey button and two-factor page method gating.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders as render } from "../../utils/renderWithProviders";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
const push = vi.fn();
const replace = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace }),
  useSearchParams: () => new URLSearchParams(search),
}));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));
vi.mock("@/lib/api/auth", () => ({
  login: vi.fn(),
  getAuthConfig: vi.fn().mockResolvedValue({
    local_auth_enabled: true,
    oauth_providers: [],
  }),
  verifyTwoFactorLogin: vi.fn(),
  oauthLoginUrl: () => "/x",
}));
vi.mock("@/lib/passkeys", () => ({
  passkeysAvailable: vi.fn(() => true),
  authenticateWithPasskey: vi.fn(),
}));
vi.mock("@/lib/auth/flow", () => ({
  completeLogin: vi.fn(),
  twoFactorUrl: (n: string) => `/two-factor?next=${n}`,
}));

import LoginPage from "@/app/(auth)/login/page";
import TwoFactorPage from "@/app/(auth)/two-factor/page";
import * as pk from "@/lib/passkeys";
import * as flow from "@/lib/auth/flow";
import { usePendingTwoFactor } from "@/stores/pendingTwoFactor";

beforeEach(() => {
  vi.clearAllMocks();
  search = "";
  usePendingTwoFactor.getState().clear();
  vi.mocked(pk.passkeysAvailable).mockReturnValue(true);
});

describe("login passkey", () => {
  it("offers passkey sign-in and webauthn autofill", async () => {
    vi.mocked(pk.authenticateWithPasskey).mockResolvedValue({} as never);
    vi.mocked(flow.completeLogin).mockResolvedValue({ kind: "authenticated" });
    render(<LoginPage />);
    expect(screen.getByLabelText("Email")).toHaveAttribute(
      "autocomplete",
      "username webauthn",
    );
    await userEvent.click(
      await screen.findByRole("button", { name: "Sign in with a passkey" }),
    );
    await waitFor(() => expect(push).toHaveBeenCalledWith("/app"));
  });

  it("hides the passkey button on insecure context", async () => {
    vi.mocked(pk.passkeysAvailable).mockReturnValue(false);
    render(<LoginPage />);
    await screen.findByLabelText("Email");
    expect(
      screen.queryByRole("button", { name: "Sign in with a passkey" }),
    ).toBeNull();
  });
});

describe("two-factor page methods", () => {
  it("passkey-only: no code input, passkey button completes login", async () => {
    usePendingTwoFactor.getState().set("T", ["passkey"]);
    vi.mocked(pk.authenticateWithPasskey).mockResolvedValue({} as never);
    vi.mocked(flow.completeLogin).mockResolvedValue({ kind: "authenticated" });
    render(<TwoFactorPage />);
    expect(screen.queryByLabelText("Code")).toBeNull();
    await userEvent.click(
      screen.getByRole("button", { name: "Use a passkey" }),
    );
    await waitFor(() =>
      expect(pk.authenticateWithPasskey).toHaveBeenCalledWith({
        pendingToken: "T",
      }),
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"));
  });

  it("totp only: code input, no passkey button", () => {
    usePendingTwoFactor.getState().set("T", ["totp", "recovery"]);
    render(<TwoFactorPage />);
    expect(screen.getByLabelText("Code")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Use a passkey" })).toBeNull();
  });

  it("passkey-only without passkey support falls back to the code form", () => {
    usePendingTwoFactor.getState().set("T", ["passkey"]);
    vi.mocked(pk.passkeysAvailable).mockReturnValue(false);
    render(<TwoFactorPage />);
    expect(screen.getByLabelText("Code")).toBeTruthy();
  });

  it("without a pending token shows the expired card", () => {
    render(<TwoFactorPage />);
    expect(screen.getByText("Back to sign-in")).toBeTruthy();
  });
});
