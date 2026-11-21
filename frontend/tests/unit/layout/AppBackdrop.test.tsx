/**
 * @file tests/unit/layout/AppBackdrop.test.tsx
 * @brief Backdrop resolves the pattern from settings, then branding, then contour.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";

const data = vi.hoisted(() => ({
  settings: undefined as unknown,
  branding: undefined as unknown,
}));
vi.mock("@/hooks/useSettings", () => ({
  useUserSettings: () => ({ data: data.settings }),
}));
vi.mock("@/hooks/useBranding", () => ({
  useBranding: () => ({ data: data.branding }),
}));

import { AppBackdrop } from "@/components/layout/AppBackdrop";
import { patternUrl } from "@/lib/patterns";

function maskOf(c: HTMLElement) {
  return (c.querySelector("[data-pattern]") as HTMLElement).getAttribute(
    "data-pattern",
  );
}

describe("AppBackdrop", () => {
  it("uses the user's pattern", () => {
    data.settings = { home_pattern: "waves" };
    data.branding = { home_pattern: "dots" };
    const { container } = render(<AppBackdrop />);
    expect(maskOf(container)).toBe("waves");
    expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
  });

  it("falls back to branding", () => {
    data.settings = { home_pattern: null };
    data.branding = { home_pattern: "dots" };
    expect(maskOf(render(<AppBackdrop />).container)).toBe("dots");
  });

  it("defaults to contour", () => {
    data.settings = { home_pattern: null };
    data.branding = undefined;
    const { container } = render(<AppBackdrop />);
    expect(maskOf(container)).toBe("contour");
    expect(patternUrl("contour")).toBeTruthy();
  });

  it("renders no pattern layer for none", () => {
    data.settings = { home_pattern: "none" };
    const { container } = render(<AppBackdrop />);
    expect(container.querySelector("[data-pattern]")).toBeNull();
  });
});
