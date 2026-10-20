/**
 * @file tests/unit/admin/BrandingTab.test.tsx
 * @brief BrandingTab AA rejection, server 422 path; BrandingStyle CSS var.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ApiError } from "@/lib/api/errors";
import * as api from "@/lib/api/branding";
import { BrandingTab } from "@/components/admin/BrandingTab";
import { BrandingStyle } from "@/components/layout/BrandingStyle";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
vi.mock("@/lib/api/branding", async (orig) => ({
  ...(await orig<typeof api>()),
  getBranding: vi.fn(),
  updateBranding: vi.fn(),
}));

const base = {
  community_name: "Garden",
  tagline: null,
  color_accent: "#C6B4F5",
  logo_light_url: null,
  logo_dark_url: null,
};

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  document.documentElement.removeAttribute("style");
  vi.mocked(api.getBranding).mockResolvedValue(base);
});

describe("BrandingTab", () => {
  it("rejects low-contrast accent and disables save", async () => {
    wrap(<BrandingTab />);
    const input = await screen.findByLabelText("Accent color");
    await userEvent.clear(input);
    await userEvent.type(input, "#14301E");
    expect(screen.getByText(/at least 4.5:1/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Save branding" }),
    ).toBeDisabled();
  });

  it("shows server 422 message", async () => {
    vi.mocked(api.updateBranding).mockRejectedValue(
      new ApiError(422, "validation_error", "Server says no"),
    );
    wrap(<BrandingTab />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Save branding" }),
    );
    expect(await screen.findByText("Server says no")).toBeInTheDocument();
  });
});

describe("BrandingStyle", () => {
  it("applies accepted accent to --nx-accent", async () => {
    vi.mocked(api.getBranding).mockResolvedValue({
      ...base,
      color_accent: "#AEE0B5",
    });
    wrap(<BrandingStyle />);
    await waitFor(() =>
      expect(
        document.documentElement.style.getPropertyValue("--nx-accent"),
      ).toBe("#AEE0B5"),
    );
  });

  it("ignores failing accent", async () => {
    vi.mocked(api.getBranding).mockResolvedValue({
      ...base,
      color_accent: "#14301E",
    });
    wrap(<BrandingStyle />);
    await waitFor(() => expect(api.getBranding).toHaveBeenCalled());
    expect(document.documentElement.style.getPropertyValue("--nx-accent")).toBe(
      "",
    );
  });
});
