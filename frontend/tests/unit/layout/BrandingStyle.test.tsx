/**
 * @file tests/unit/layout/BrandingStyle.test.tsx
 * @brief BrandingStyle applies palette/fonts, skips invalid hex, cleans up.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/react";

const state: { data: unknown } = { data: undefined };
vi.mock("@/hooks/useBranding", () => ({ useBranding: () => state }));

import { BrandingStyle } from "@/components/layout/BrandingStyle";

const base = {
  community_name: "C",
  tagline: null,
  logo_light_url: null,
  logo_dark_url: null,
  color_primary: "#112233",
  color_primary_dark: "#223344",
  color_accent: "#c6b4f5",
  color_surface_light: "#ffffff",
  color_surface_dark: "#101010",
  color_text_light: "#111827",
  color_text_dark: "#f9fafb",
  font_family: "Inter",
  font_family_mono: "JetBrains Mono",
};
const root = () => document.documentElement;
const darkCss = () => document.getElementById("nx-branding-dark")?.textContent;

describe("BrandingStyle", () => {
  beforeEach(() => {
    root().removeAttribute("style");
    document.getElementById("nx-branding-dark")?.remove();
  });

  it("sets light vars, fonts and dark scoped style", () => {
    state.data = base;
    render(<BrandingStyle />);
    expect(root().style.getPropertyValue("--nx-surface")).toBe("#ffffff");
    expect(root().style.getPropertyValue("--nx-ink")).toBe("#111827");
    expect(root().style.getPropertyValue("--nx-surface-strong")).toBe(
      "#112233",
    );
    expect(root().style.getPropertyValue("--font-sans")).toContain("Inter");
    expect(root().style.getPropertyValue("--font-mono")).toContain(
      "JetBrains Mono",
    );
    expect(darkCss()).toContain(".dark");
    expect(darkCss()).toContain("--nx-surface:#101010");
    expect(darkCss()).toContain("--nx-ink:#f9fafb");
    expect(darkCss()).toContain("--nx-surface-strong:#223344");
  });

  it("skips invalid hex and unsafe fonts", () => {
    state.data = {
      ...base,
      color_surface_light: "red",
      color_text_dark: "#12",
      color_primary: "url(x)",
      font_family: "x;}body{display:none",
    };
    render(<BrandingStyle />);
    expect(root().style.getPropertyValue("--nx-surface")).toBe("");
    expect(root().style.getPropertyValue("--nx-surface-strong")).toBe("");
    expect(root().style.getPropertyValue("--font-sans")).toBe("");
    expect(darkCss()).not.toContain("--nx-ink");
  });

  it("removes everything on unmount", () => {
    state.data = base;
    const { unmount } = render(<BrandingStyle />);
    unmount();
    for (const v of [
      "--nx-surface",
      "--nx-ink",
      "--nx-surface-strong",
      "--nx-accent",
      "--font-sans",
      "--font-mono",
    ])
      expect(root().style.getPropertyValue(v)).toBe("");
    expect(darkCss()).toBeUndefined();
  });
});
