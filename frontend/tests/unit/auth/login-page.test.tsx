/**
 * @file tests/unit/auth/login-page.test.tsx
 * @brief Login page: submit calls login, error shown on the form, OAuth
 *        buttons render from config.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
let search = "";
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
    expect(await screen.findByRole("alert")).toBeTruthy();
  });

  it("renders OAuth providers from config", async () => {
    render(<LoginPage />);
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
    render(<LoginPage />);
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "pw");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith(expected));
  });
});
