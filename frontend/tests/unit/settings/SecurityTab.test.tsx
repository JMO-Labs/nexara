/**
 * @file tests/unit/settings/SecurityTab.test.tsx
 * @brief Security tab: TOTP confirm shows 10 codes, passkeys hidden when
 *        insecure; admin Reset 2FA confirm posts.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders as render } from "../../utils/renderWithProviders";

vi.mock("qrcode", () => ({
  default: { toDataURL: vi.fn().mockResolvedValue("data:image/png;base64,xx") },
}));
vi.mock("@/lib/auth/session", () => ({
  refreshAccessToken: vi.fn().mockResolvedValue("t"),
}));
vi.mock("@/lib/api/twoFactor");

import { SecurityTab } from "@/components/settings/SecurityTab";
import { ResetTwoFactorButton } from "@/components/admin/ResetTwoFactorButton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import * as api from "@/lib/api/twoFactor";

const setSecure = (v: boolean) =>
  Object.defineProperty(window, "isSecureContext", {
    value: v,
    configurable: true,
  });

beforeEach(() => {
  vi.clearAllMocks();
  setSecure(true);
  vi.mocked(api.getTwoFactorStatus).mockResolvedValue({
    totp: false,
    passkeys: 0,
    recovery_left: 0,
    required: false,
    grace_until: null,
  });
  vi.mocked(api.listPasskeys).mockResolvedValue([]);
});

describe("SecurityTab", () => {
  it("confirm flow shows 10 recovery codes gated by the checkbox", async () => {
    const codes = Array.from({ length: 10 }, (_, i) => `code-${i}`);
    vi.mocked(api.totpStart).mockResolvedValue({
      otpauth_uri: "otpauth://totp/x",
      secret: "SECRET",
    });
    vi.mocked(api.totpConfirm).mockResolvedValue({ recovery_codes: codes });
    render(<SecurityTab />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Set up authenticator" }),
    );
    expect(
      await screen.findByAltText("QR code for authenticator app"),
    ).toBeTruthy();
    const input = screen.getByLabelText("6-digit code");
    expect(input).toHaveAttribute("autocomplete", "one-time-code");
    expect(input).toHaveAttribute("inputmode", "numeric");
    await userEvent.type(input, "123456");
    await userEvent.click(screen.getByRole("button", { name: "Turn on" }));
    const list = await screen.findByRole("list", { name: "Recovery codes" });
    expect(list.querySelectorAll("li")).toHaveLength(10);
    expect(api.totpConfirm).toHaveBeenCalledWith("123456");
    const done = screen.getByRole("button", { name: "Done" });
    expect(done).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    expect(done).toBeEnabled();
  });

  it("hides passkey controls on insecure context", async () => {
    setSecure(false);
    render(<SecurityTab />);
    expect(
      await screen.findByText("Passkeys need a secure (HTTPS) connection."),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Add a passkey" })).toBeNull();
  });

  it("shows the add-passkey button on secure context", async () => {
    render(<SecurityTab />);
    expect(
      await screen.findByRole("button", { name: "Add a passkey" }),
    ).toBeTruthy();
  });
});

describe("ResetTwoFactorButton", () => {
  it("confirms then posts the reset", async () => {
    vi.mocked(api.resetUserTwoFactor).mockResolvedValue({ message: "ok" });
    render(
      <>
        <ResetTwoFactorButton userId="u1" name="Ann" />
        <ConfirmDialog />
      </>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Reset 2FA" }));
    expect(api.resetUserTwoFactor).not.toHaveBeenCalled();
    const buttons = await screen.findAllByRole("button", { name: "Reset 2FA" });
    await userEvent.click(buttons[buttons.length - 1]);
    await waitFor(() =>
      expect(api.resetUserTwoFactor).toHaveBeenCalledWith("u1"),
    );
  });
});
