/**
 * @file tests/unit/layout/GraceBanner.test.tsx
 * @brief Grace banner shows only while 2FA is required and unset.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders as render } from "../../utils/renderWithProviders";

vi.mock("@/lib/api/twoFactor");
import { GraceBanner } from "@/components/layout/GraceBanner";
import * as api from "@/lib/api/twoFactor";

const st = (o: object) => ({
  totp: false,
  passkeys: 0,
  recovery_left: 0,
  required: true,
  grace_until: "2030-01-02T00:00:00Z",
  ...o,
});

describe("GraceBanner", () => {
  it("links to Security settings with the date", async () => {
    vi.mocked(api.getTwoFactorStatus).mockResolvedValue(st({}));
    render(<GraceBanner />);
    expect(await screen.findByText(/Set it up by/)).toBeTruthy();
    expect(
      screen.getByRole("link", { name: /security settings/i }),
    ).toHaveAttribute("href", "/app/settings?tab=security");
  });

  it("is hidden once set up", async () => {
    vi.mocked(api.getTwoFactorStatus).mockResolvedValue(st({ totp: true }));
    render(<GraceBanner />);
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByRole("status")).toBeNull();
  });
});
