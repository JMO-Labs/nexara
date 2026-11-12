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
  color_primary: "#14301e",
  color_primary_dark: "#1b3524",
  color_accent: "#C6B4F5",
  color_surface_light: "#ffffff",
  color_surface_dark: "#16291d",
  color_text_light: "#14301e",
  color_text_dark: "#dce9d8",
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
  it("saves name when the stored accent is legacy low-contrast, without resending it", async () => {
    vi.mocked(api.getBranding).mockResolvedValue({
      ...base,
      color_accent: "#8b5cf6",
    });
    vi.mocked(api.updateBranding).mockResolvedValue({
      branding: { ...base, community_name: "Soto crew" },
    });
    wrap(<BrandingTab />);
    const name = await screen.findByLabelText("Community name");
    await userEvent.clear(name);
    await userEvent.type(name, "Soto crew");
    const save = screen.getByRole("button", { name: /save/i });
    expect(save).toBeEnabled();
    await userEvent.click(save);
    await waitFor(() => expect(api.updateBranding).toHaveBeenCalled());
    expect(vi.mocked(api.updateBranding).mock.calls[0][0]).not.toHaveProperty(
      "color_accent",
    );
  });

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

describe("BrandingTab full palette", () => {
  it("renders all 7 palette color inputs", async () => {
    wrap(<BrandingTab />);
    for (const l of [
      "Primary",
      "Primary (dark)",
      "Accent color",
      "Surface (light)",
      "Surface (dark)",
      "Text (light)",
      "Text (dark)",
    ])
      expect(await screen.findByLabelText(l)).toBeInTheDocument();
  });

  it("warns, not blocks, on low text contrast", async () => {
    wrap(<BrandingTab />);
    const input = await screen.findByLabelText("Text (light)");
    await userEvent.clear(input);
    await userEvent.type(input, "#eeeeee");
    expect((await screen.findAllByRole("status")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Save branding" })).toBeEnabled();
  });

  it("updates live preview and submits only changed colors", async () => {
    vi.mocked(api.updateBranding).mockResolvedValue({ branding: base });
    wrap(<BrandingTab />);
    const input = await screen.findByLabelText("Surface (dark)");
    await userEvent.clear(input);
    await userEvent.type(input, "#101010");
    expect(screen.getByTestId("branding-preview-dark")).toHaveStyle({
      backgroundColor: "#101010",
    });
    await userEvent.click(
      screen.getByRole("button", { name: "Save branding" }),
    );
    await waitFor(() => expect(api.updateBranding).toHaveBeenCalled());
    const body = vi.mocked(api.updateBranding).mock.calls[0][0];
    expect(body.color_surface_dark).toBe("#101010");
    expect(body).not.toHaveProperty("color_primary");
  });

  it("disables save on invalid hex", async () => {
    wrap(<BrandingTab />);
    const input = await screen.findByLabelText("Primary");
    await userEvent.clear(input);
    await userEvent.type(input, "zzz");
    expect(
      screen.getByRole("button", { name: "Save branding" }),
    ).toBeDisabled();
  });
});
