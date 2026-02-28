/**
 * @file tests/composables/useBranding.test.ts
 * @brief TDD tests for the useBranding composable.
 *
 * Verifies CSS variable injection and branding data fetching.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { useBranding } from "~/composables/useBranding";

describe("useBranding", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    document.documentElement.style.removeProperty("--color-primary");
    document.documentElement.style.removeProperty("--color-primary-dark");
  });

  it("injects CSS variables from fetched branding data", async () => {
    const mockBranding = {
      community_name: "TestCommunity",
      tagline: "Welcome",
      color_primary: "#ff5500",
      color_primary_dark: "#cc4400",
      logo_light_url: null,
      logo_dark_url: null,
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockBranding,
    } as Response);

    const { fetchBranding, branding } = useBranding();
    await fetchBranding();

    expect(branding.value.community_name).toBe("TestCommunity");
    expect(
      document.documentElement.style.getPropertyValue("--color-primary"),
    ).toBe("#ff5500");
    expect(
      document.documentElement.style.getPropertyValue("--color-primary-dark"),
    ).toBe("#cc4400");
  });

  it("falls back to defaults on fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
      new Error("Network error"),
    );

    const { fetchBranding, branding } = useBranding();
    await fetchBranding();

    expect(branding.value.community_name).toBe("Nexara");
    expect(
      document.documentElement.style.getPropertyValue("--color-primary"),
    ).toBe("#3b82f6");
  });

  it("sets loaded to true after successful fetch", async () => {
    const mockBranding = {
      community_name: "Loaded",
      tagline: null,
      color_primary: "#3b82f6",
      color_primary_dark: "#2563eb",
      logo_light_url: null,
      logo_dark_url: null,
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => mockBranding,
    } as Response);

    const { fetchBranding, loaded } = useBranding();
    await fetchBranding();

    expect(loaded.value).toBe(true);
  });
});
