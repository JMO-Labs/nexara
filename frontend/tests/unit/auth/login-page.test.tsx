/**
 * @file tests/unit/auth/login-page.test.tsx
 * @brief Login page: submit calls login, error toast, OAuth
 *        buttons render from config.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders as render } from "../../utils/renderWithProviders";
import { useToasts } from "@/stores/toasts";
import userEvent from "@testing-library/user-event";

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
  getAuthConfig: vi.fn(),
  oauthLoginUrl: (slug: string) => `/oauth/${slug}`,
}));
vi.mock("@/lib/auth/flow", () => ({ completeLogin: vi.fn() }));

import LoginPage from "@/app/(auth)/login/page";
import * as api from "@/lib/api/auth";
import * as flow from "@/lib/auth/flow";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    search = "";
    vi.mocked(api.getAuthConfig).mockResolvedValue({
      oidc_enabled: true,
      registration_enabled: true,
      local_auth_enabled: true,
      oauth_providers: [{ slug: "g", display_name: "Continue with Google", icon_url: null }],
    });
  });

  it("submits credentials and navigates", async () => {
    vi.mocked(api.login).mockResolvedValue({} as never);
    vi.mocked(flow.completeLogin).mockResolvedValue({ kind: "ok" } as never);
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() =>
      expect(api.login).toHaveBeenCalledWith("a@b.com", "pw"),
    );
    await waitFor(() => expect(push).toHaveBeenCalledWith("/app"));
  });

  it("shows the error on failure", async () => {
    vi.mocked(api.login).mockRejectedValue(new Error("nope"));
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() =>
      expect(useToasts.getState().items.at(-1)).toMatchObject({
        variant: "danger",
        message: "toasts.auth.login.failed",
      }),
    );
  });

  it("renders OAuth providers from config", async () => {
    render(<LoginPage />);
    const link = await screen.findByRole("link", { name: "Continue with Google" });
    expect(link.getAttribute("href")).toBe("/oauth/g");
  });

  it.each([
    ["https://evil.example", "/app"],
    ["//evil.example", "/app"],
    ["/app/events", "/app/events"],
  ])("next=%s navigates to %s", async (next, expected) => {
    search = `next=${encodeURIComponent(next)}`;
    vi.mocked(api.login).mockResolvedValue({} as never);
    vi.mocked(flow.completeLogin).mockResolvedValue({ kind: "ok" } as never);
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith(expected));
  });

  it("hides email/password form when SSO-only", async () => {
    vi.mocked(api.getAuthConfig).mockResolvedValue({
      oidc_enabled: true,
      registration_enabled: false,
      local_auth_enabled: false,
      sso_only: true,
      oauth_providers: [{ slug: "g", display_name: "Continue with Google", icon_url: null }],
    });
    render(<LoginPage />);
    expect(await screen.findByRole("link", { name: /Google/ })).toBeTruthy();
    expect(screen.queryByLabelText("Email")).toBeNull();
    expect(screen.queryByLabelText("Password")).toBeNull();
    expect(screen.getByText("Sign in with SSO")).toBeTruthy();
  });

  it("shows divider between form and SSO buttons", async () => {
    render(<LoginPage />);
    await screen.findByRole("link", { name: /Google/ });
    expect(screen.getByRole("separator")).toBeTruthy();
    expect(screen.getByLabelText("Email")).toBeTruthy();
  });
});

describe("LoginPage validation", () => {
  it("shows inline email format error on submit and does not submit", async () => {
    vi.mocked(api.getAuthConfig).mockResolvedValue({
      oidc_enabled: false,
      registration_enabled: true,
      local_auth_enabled: true,
      oauth_providers: [],
    });
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "not-an-email");
    await userEvent.tab();
    // No blur validation (the passkey button leaves the field too).
    expect(screen.queryByText("Enter a valid email address")).toBeNull();
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter a valid email address")).toBeTruthy();
    expect(api.login).not.toHaveBeenCalled();
  });

  it("disables inputs and shows a spinner while submitting", async () => {
    vi.mocked(api.login).mockReturnValue(new Promise(() => {}));
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    const btn = screen.getByRole("button", { name: "Sign in" });
    await userEvent.click(btn);
    await waitFor(() => expect(btn).toBeDisabled());
    expect(btn).toHaveAttribute("aria-busy", "true");
    expect(btn.querySelector("svg")).not.toBeNull();
    expect(screen.getByLabelText("Email")).toBeDisabled();
    expect(screen.getByLabelText("Password")).toBeDisabled();
  });
});

describe("LoginPage SSO errors", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getAuthConfig).mockResolvedValue({
      oidc_enabled: true,
      registration_enabled: true,
      local_auth_enabled: true,
      oauth_providers: [],
    });
  });

  it("shows mapped alert and clears the param", async () => {
    search = "error=sso_domain_not_allowed&provider=Acme&next=%2Fapp%2Fx";
    render(<LoginPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your Acme account isn't allowed to sign in here.",
    );
    expect(replace).toHaveBeenCalledWith("/login?next=%2Fapp%2Fx");
  });

  it("maps no_account, falls back on unknown, never echoes raw code", async () => {
    search = "error=sso_no_account";
    const { unmount } = render(<LoginPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your account isn't set up here yet. Ask an admin for an invite.",
    );
    unmount();
    search = "error=<img src=x>";
    render(<LoginPage />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Sign-in didn't work. Please try again.");
    expect(alert.innerHTML).not.toContain("<img");
  });

  it("uses provider fallback name", async () => {
    search = "error=sso_group_required";
    render(<LoginPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your sign-in provider account isn't allowed",
    );
  });
});
