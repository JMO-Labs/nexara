/**
 * @file tests/unit/auth/auth-blur-validation.test.tsx
 * @brief Inline email-format / password-length validation on blur for the
 *        register, magic-link, reset-password and two-factor pages.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders as render } from "../../utils/renderWithProviders";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
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
  register: vi.fn(),
  requestMagicLink: vi.fn(),
  requestPasswordReset: vi.fn(),
  confirmPasswordReset: vi.fn(),
  verifyTwoFactorLogin: vi.fn(),
}));
vi.mock("@/lib/auth/flow", () => ({ completeLogin: vi.fn() }));

import RegisterPage from "@/app/(auth)/register/page";
import MagicLinkPage from "@/app/(auth)/magic-link/page";
import ResetPasswordPage from "@/app/(auth)/reset-password/page";
import TwoFactorPage from "@/app/(auth)/two-factor/page";

const EMAIL_ERR = "Enter a valid email address";

describe("auth blur validation", () => {
  beforeEach(() => {
    search = "";
  });

  it("register validates email and password on blur", async () => {
    render(<RegisterPage />);
    const u = userEvent.setup();
    await u.type(screen.getByLabelText("Email"), "nope");
    await u.tab();
    expect(await screen.findByText(EMAIL_ERR)).toBeInTheDocument();
    await u.type(screen.getByLabelText("Password"), "short");
    await u.tab();
    expect(
      await screen.findByText("At least 12 characters"),
    ).toBeInTheDocument();
  });

  it("magic-link validates email on blur", async () => {
    render(<MagicLinkPage />);
    const u = userEvent.setup();
    await u.type(screen.getByLabelText("Email"), "nope");
    await u.tab();
    expect(await screen.findByText(EMAIL_ERR)).toBeInTheDocument();
  });

  it("reset request validates email on blur", async () => {
    render(<ResetPasswordPage />);
    const u = userEvent.setup();
    await u.type(screen.getByLabelText("Email"), "nope");
    await u.tab();
    expect(await screen.findByText(EMAIL_ERR)).toBeInTheDocument();
  });

  it("reset confirm validates password length on blur", async () => {
    search = "token=t";
    render(<ResetPasswordPage />);
    const u = userEvent.setup();
    await u.type(screen.getByLabelText("New password"), "short");
    await u.tab();
    const hits = await screen.findAllByText("At least 12 characters");
    expect(hits.length).toBeGreaterThan(0);
    expect(screen.getByLabelText("New password")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("two-factor validates code length on blur", async () => {
    search = "token=t";
    render(<TwoFactorPage />);
    const u = userEvent.setup();
    await u.type(screen.getByLabelText("Code"), "12");
    await u.tab();
    expect(
      await screen.findByText("Enter the 6-digit code"),
    ).toBeInTheDocument();
  });
});
