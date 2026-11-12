/**
 * @file tests/unit/admin/ThemeGallery.test.tsx
 * @brief ThemeGallery renders presets, marks the active one, applies on click.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as api from "@/lib/api/branding";
import { ThemeGallery } from "@/components/admin/ThemeGallery";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));
vi.mock("@/lib/api/branding", async (orig) => ({
  ...(await orig<typeof api>()),
  getPresetThemes: vi.fn(),
  applyPresetTheme: vi.fn(),
}));

const ocean = {
  name: "Ocean",
  description: "Cool blues",
  primary: "#0369a1",
  primary_dark: "#075985",
  accent: "#67e8f9",
  surface_light: "#f0f9ff",
  surface_dark: "#0c2d47",
  text_light: "#0c2341",
  text_dark: "#f5f9fc",
};
const forest = {
  ...ocean,
  name: "Forest",
  description: "Greens",
  primary: "#15803d",
};
const current = {
  community_name: "G",
  tagline: null,
  logo_light_url: null,
  logo_dark_url: null,
  color_primary: ocean.primary,
  color_primary_dark: ocean.primary_dark,
  color_accent: ocean.accent,
  color_surface_light: ocean.surface_light,
  color_surface_dark: ocean.surface_dark,
  color_text_light: ocean.text_light,
  color_text_dark: ocean.text_dark,
};

function setup() {
  vi.mocked(api.getPresetThemes).mockResolvedValue({ themes: [ocean, forest] });
  vi.mocked(api.applyPresetTheme).mockResolvedValue({ branding: current });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <ThemeGallery current={current} />
    </QueryClientProvider>,
  );
}

describe("ThemeGallery", () => {
  it("renders cards and marks the matching one selected", async () => {
    setup();
    const o = await screen.findByRole("button", { name: "Apply Ocean theme" });
    expect(o).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("button", { name: "Apply Forest theme" }),
    ).toHaveAttribute("aria-pressed", "false");
    expect(
      screen.getByText(/apply all colors in one click/),
    ).toBeInTheDocument();
  });

  it("applies a theme on click", async () => {
    setup();
    await userEvent.click(
      await screen.findByRole("button", { name: "Apply Forest theme" }),
    );
    await waitFor(() => expect(api.applyPresetTheme).toHaveBeenCalled());
    expect(vi.mocked(api.applyPresetTheme).mock.calls[0][0]).toBe("Forest");
  });
});
