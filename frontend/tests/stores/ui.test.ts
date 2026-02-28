/**
 * @file tests/stores/ui.test.ts
 * @brief TDD tests for the UI Pinia store.
 *
 * Tests dark mode toggle, search modal state, and toast notifications.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useUiStore } from "~/stores/ui";

describe("ui store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("starts with default state", () => {
    const store = useUiStore();

    expect(store.darkMode).toBe(false);
    expect(store.searchOpen).toBe(false);
    expect(store.toasts).toEqual([]);
  });

  it("toggleDarkMode() flips the dark mode flag", () => {
    const store = useUiStore();

    store.toggleDarkMode();
    expect(store.darkMode).toBe(true);

    store.toggleDarkMode();
    expect(store.darkMode).toBe(false);
  });

  it("toggleDarkMode() persists preference to localStorage", () => {
    const store = useUiStore();

    store.toggleDarkMode();
    expect(localStorage.getItem("nexara-dark-mode")).toBe("true");

    store.toggleDarkMode();
    expect(localStorage.getItem("nexara-dark-mode")).toBe("false");
  });

  it("initializes dark mode from localStorage", () => {
    localStorage.setItem("nexara-dark-mode", "true");

    const store = useUiStore();
    store.initDarkMode();

    expect(store.darkMode).toBe(true);
  });

  it("initializes dark mode from system preference when no saved pref", () => {
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

    const store = useUiStore();
    store.initDarkMode();

    expect(store.darkMode).toBe(true);
  });

  it("openSearch() sets searchOpen to true", () => {
    const store = useUiStore();

    store.openSearch();
    expect(store.searchOpen).toBe(true);
  });

  it("closeSearch() sets searchOpen to false", () => {
    const store = useUiStore();

    store.openSearch();
    store.closeSearch();
    expect(store.searchOpen).toBe(false);
  });

  it("showToast() adds a toast notification", () => {
    const store = useUiStore();

    store.showToast({ type: "success", message: "It worked!" });

    expect(store.toasts).toHaveLength(1);
    expect(store.toasts[0].type).toBe("success");
    expect(store.toasts[0].message).toBe("It worked!");
    expect(store.toasts[0].id).toBeDefined();
  });

  it("showToast() supports multiple toasts", () => {
    const store = useUiStore();

    store.showToast({ type: "success", message: "First" });
    store.showToast({ type: "error", message: "Second" });

    expect(store.toasts).toHaveLength(2);
  });

  it("dismissToast() removes a specific toast", () => {
    const store = useUiStore();

    store.showToast({ type: "info", message: "To dismiss" });
    const toastId = store.toasts[0].id;

    store.dismissToast(toastId);

    expect(store.toasts).toHaveLength(0);
  });
});
