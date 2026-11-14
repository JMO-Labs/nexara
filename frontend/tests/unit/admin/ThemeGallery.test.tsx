/**
 * @file tests/unit/admin/ThemeGallery.test.tsx
 * @brief ThemeGallery renders preset cards, marks current, applies on click.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as api from "@/lib/api/branding";
import { ThemeGallery } from "@/components/admin/ThemeGallery";

vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));

vi.mock("@/lib/api/branding", async (orig) => ({
  ...(await orig<typeof api>()),
  listPresets: vi.fn(),
  applyPreset: vi.fn(),
}));

const themes = [
  {
    name: "Ocean",
    description: "Cool blues",
    primary: "#0284c7",
    primary_dark: "#0369a1",
    accent: "#06b6d4",
    surface_light: "#f0f9ff",
    surface_dark: "#0c2d47",
    text_light: "#0c2341",
    text_dark: "#f5f9fc",
  },
  {
    name: "Forest",
    description: "Deep greens",
    primary: "#15803d",
    primary_dark: "#166534",
    accent: "#86efac",
    surface_light: "#f0fdf4",
    surface_dark: "#0f2a1a",
    text_light: "#0f2a1a",
    text_dark: "#f2fbf5",
  },
];

function wrap(current?: Partial<api.Branding>) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ThemeGallery current={current} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listPresets).mockResolvedValue({ themes });
  vi.mocked(api.applyPreset).mockResolvedValue({
    branding: {} as api.Branding,
  });
});

describe("ThemeGallery", () => {
  it("renders a card per theme with info text", async () => {
    wrap();
    expect(await screen.findByText("Ocean")).toBeInTheDocument();
    expect(screen.getByText("Forest")).toBeInTheDocument();
    expect(
      screen.getByText(/apply all colors in one click/i),
    ).toBeInTheDocument();
  });

  it("applies a theme on click", async () => {
    wrap();
    await userEvent.click(
      await screen.findByRole("button", { name: /apply ocean/i }),
    );
    await waitFor(() =>
      expect(vi.mocked(api.applyPreset).mock.calls[0][0]).toBe("Ocean"),
    );
  });

  it("marks the theme matching current colors", async () => {
    wrap({
      color_primary: "#15803D",
      color_primary_dark: "#166534",
      color_accent: "#86efac",
      color_surface_light: "#f0fdf4",
      color_surface_dark: "#0f2a1a",
      color_text_light: "#0f2a1a",
      color_text_dark: "#f2fbf5",
    });
    const btn = await screen.findByRole("button", { name: /apply forest/i });
    expect(btn).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("button", { name: /apply ocean/i }),
    ).toHaveAttribute("aria-pressed", "false");
  });
});
