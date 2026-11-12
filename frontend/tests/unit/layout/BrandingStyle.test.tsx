/**
 * @file tests/unit/layout/BrandingStyle.test.tsx
 * @brief BrandingStyle applies full palette + fonts, skips invalid hex, cleans up.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as api from "@/lib/api/branding";
import type { Branding } from "@/lib/api/branding";
import { BrandingStyle } from "@/components/layout/BrandingStyle";

vi.mock("@/lib/api/branding", async (orig) => ({
  ...(await orig<typeof api>()),
  getBranding: vi.fn(),
}));

const full: Branding = {
  community_name: "Garden",
  tagline: null,
  color_accent: "#C6B4F5",
  logo_light_url: null,
  logo_dark_url: null,
  color_primary: "#112233",
  color_primary_dark: "#223344",
  color_surface_light: "#fafafa",
  color_surface_dark: "#101010",
  color_text_light: "#0a0a0a",
  color_text_dark: "#eeeeee",
  font_family: "Inter",
  font_family_mono: "JetBrains Mono",
};

const root = () => document.documentElement;
const prop = (n: string) => root().style.getPropertyValue(n);

function mount() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <BrandingStyle />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  root().removeAttribute("style");
  root().classList.remove("dark");
});

describe("BrandingStyle", () => {
  it("sets light palette and font vars", async () => {
    vi.mocked(api.getBranding).mockResolvedValue(full);
    mount();
    await waitFor(() => expect(prop("--nx-surface")).toBe("#fafafa"));
    expect(prop("--nx-ink")).toBe("#0a0a0a");
    expect(prop("--nx-surface-strong")).toBe("#112233");
    expect(prop("--nx-accent")).toBe("#C6B4F5");
    expect(prop("--font-sans")).toContain('"Inter"');
    expect(prop("--font-sans")).toContain("sans-serif");
    expect(prop("--font-mono")).toContain('"JetBrains Mono"');
    expect(prop("--font-mono")).toContain("monospace");
  });

  it("uses dark values when html has .dark and follows toggles", async () => {
    root().classList.add("dark");
    vi.mocked(api.getBranding).mockResolvedValue(full);
    mount();
    await waitFor(() => expect(prop("--nx-surface")).toBe("#101010"));
    expect(prop("--nx-ink")).toBe("#eeeeee");
    expect(prop("--nx-surface-strong")).toBe("#223344");
    root().classList.remove("dark");
    await waitFor(() => expect(prop("--nx-surface")).toBe("#fafafa"));
  });

  it("skips invalid or missing hex and unsafe fonts", async () => {
    vi.mocked(api.getBranding).mockResolvedValue({
      ...full,
      color_surface_light: "red;}",
      color_text_light: "#12",
      font_family: "x;}body{",
    });
    root().style.setProperty("--nx-ink", "#123456");
    mount();
    await waitFor(() => expect(prop("--nx-surface-strong")).toBe("#112233"));
    expect(prop("--nx-surface")).toBe("");
    expect(prop("--nx-ink")).toBe("");
    expect(prop("--font-sans")).toBe("");
  });

  it("removes all properties on unmount", async () => {
    vi.mocked(api.getBranding).mockResolvedValue(full);
    const { unmount } = mount();
    await waitFor(() => expect(prop("--nx-surface")).toBe("#fafafa"));
    unmount();
    for (const n of [
      "--nx-surface",
      "--nx-ink",
      "--nx-surface-strong",
      "--nx-accent",
      "--font-sans",
      "--font-mono",
    ]) {
      expect(prop(n)).toBe("");
    }
  });
});
