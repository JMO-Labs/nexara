/**
 * @file tests/unit/auth/login-page.test.tsx
 * @brief Login page: submit calls login, error shown as a toast, OAuth
 *        buttons render from config.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/tests/utils/renderWithProviders";
import { useToasts } from "@/stores/toasts";

const push = vi.fn();
let search = "";
vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) => k,
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
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
    useToasts.getState().clear();
    search = "";
    vi.mocked(api.getAuthConfig).mockResolvedValue({
      oidc_enabled: true,
      registration_enabled: true,
      local_auth_enabled: true,
      oauth_providers: [{ slug: "g", display_name: "Google", icon_url: null }],
    });
  });

  it("submits credentials and navigates", async () => {
    vi.mocked(api.login).mockResolvedValue({} as never);
    vi.mocked(flow.completeLogin).mockResolvedValue({ kind: "ok" } as never);
    renderWithProviders(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() =>
      expect(api.login).toHaveBeenCalledWith("a@b.com", "pw"),
    );
    await waitFor(() => expect(push).toHaveBeenCalledWith("/app"));
  });

  it("shows an error toast on failure", async () => {
    vi.mocked(api.login).mockRejectedValue(new Error("nope"));
    renderWithProviders(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() =>
      expect(useToasts.getState().items.at(-1)).toMatchObject({
        variant: "danger",
        message: "toasts.auth.login.failed",
      }),
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("renders OAuth providers from config", async () => {
    renderWithProviders(<LoginPage />);
    const link = await screen.findByRole("link", { name: "Google" });
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
    renderWithProviders(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith(expected));
  });
});
