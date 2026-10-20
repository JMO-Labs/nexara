/**
 * @file tests/unit/auth/auth-leftovers.test.tsx
 * @brief Register, magic-link, two-factor, landing and offline pages.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const push = vi.fn();
const replace = vi.fn();
let search = "";
let hasCookie = false;
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace }),
  useSearchParams: () => new URLSearchParams(search),
  redirect: (to: string) => {
    throw new Error(`REDIRECT:${to}`);
  },
}));
vi.mock("next/headers", () => ({
  cookies: async () => ({ has: () => hasCookie }),
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
  register: vi.fn(),
  requestMagicLink: vi.fn(),
  verifyTwoFactorLogin: vi.fn(),
}));
vi.mock("@/lib/auth/flow", () => ({ completeLogin: vi.fn() }));

import RegisterPage from "@/app/(auth)/register/page";
import MagicLinkPage from "@/app/(auth)/magic-link/page";
import TwoFactorPage from "@/app/(auth)/two-factor/page";
import Home from "@/app/page";
import OfflinePage from "@/app/offline/page";
import * as api from "@/lib/api/auth";

beforeEach(() => {
  vi.clearAllMocks();
  search = "";
  hasCookie = false;
});

describe("auth leftovers", () => {
  it("register submits with invite token", async () => {
    search = "invite=abc";
    vi.mocked(api.register).mockResolvedValue({} as never);
    render(<RegisterPage />);
    const u = userEvent.setup();
    await u.type(screen.getByLabelText("Display name"), "Al");
    await u.type(screen.getByLabelText("Username"), "al_1");
    await u.type(screen.getByLabelText("Email"), "a@b.co");
    await u.type(screen.getByLabelText("Password"), "twelvecharsss");
    await u.click(screen.getByRole("button", { name: "Create account" }));
    await waitFor(() =>
      expect(api.register).toHaveBeenCalledWith(
        expect.objectContaining({ invite_token: "abc", username: "al_1" }),
      ),
    );
  });

  it("magic link shows confirmation after send", async () => {
    vi.mocked(api.requestMagicLink).mockResolvedValue(undefined as never);
    render(<MagicLinkPage />);
    const u = userEvent.setup();
    await u.type(screen.getByLabelText("Email"), "a@b.co");
    await u.click(screen.getByRole("button", { name: "Email me a link" }));
    expect(await screen.findByText("Check your inbox")).toBeInTheDocument();
  });

  it("two-factor without token shows expired state", () => {
    render(<TwoFactorPage />);
    expect(screen.getByText("Two-factor session expired")).toBeInTheDocument();
  });

  it("two-factor rejects an unsafe next param", async () => {
    search = "token=t&next=//evil.com";
    vi.mocked(api.verifyTwoFactorLogin).mockResolvedValue({} as never);
    render(<TwoFactorPage />);
    const u = userEvent.setup();
    await u.type(screen.getByLabelText("Code"), "123456");
    await u.click(screen.getByRole("button", { name: "Verify" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/app"));
  });

  it("landing redirects signed-in users and welcomes others", async () => {
    hasCookie = true;
    await expect(Home()).rejects.toThrow("REDIRECT:/app");
    hasCookie = false;
    render(await Home());
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("offline page has retry link", () => {
    render(<OfflinePage />);
    expect(screen.getByRole("link", { name: "Retry" })).toHaveAttribute(
      "href",
      "/app",
    );
  });
});
