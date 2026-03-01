/**
 * @file tests/composables/useDarkMode.test.ts
 * @brief TDD tests for the useDarkMode composable.
 *
 * Verifies dark class toggling on the document element,
 * localStorage persistence, and system preference detection.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useDarkMode } from "~/composables/useDarkMode";

describe("useDarkMode", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    document.documentElement.classList.remove("dark");
    vi.restoreAllMocks();
  });

  it("toggles dark class on document element", () => {
    const { toggle } = useDarkMode();

    toggle();
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    toggle();
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("exposes reactive isDark state", () => {
    const { isDark, toggle } = useDarkMode();

    expect(isDark.value).toBe(false);

    toggle();
    expect(isDark.value).toBe(true);
  });

  it("initializes from localStorage on creation", () => {
    localStorage.setItem("nexara-dark-mode", "true");

    const { isDark } = useDarkMode();

    expect(isDark.value).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("respects system preference when no saved preference", () => {
    vi.spyOn(globalThis, "matchMedia").mockReturnValue({
      matches: true,
      media: "(prefers-color-scheme: dark)",
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    });

    const { isDark } = useDarkMode();

    expect(isDark.value).toBe(true);
  });

  it("saves preference to localStorage on toggle", () => {
    const { toggle } = useDarkMode();

    toggle();
    expect(localStorage.getItem("nexara-dark-mode")).toBe("true");

    toggle();
    expect(localStorage.getItem("nexara-dark-mode")).toBe("false");
  });

  it("does not throw when localStorage is unavailable (SSR)", () => {
    const originalWindow = globalThis.window;
    vi.stubGlobal("window", undefined);

    expect(() => useDarkMode()).not.toThrow();

    vi.stubGlobal("window", originalWindow);
  });
});
