/**
 * @file tests/setup.ts
 * @brief Vitest setup. RTL matchers + cleanup.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// jsdom lacks matchMedia (used by MUI Joy color-scheme + reduced-motion).
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

// jsdom lacks ResizeObserver (Radix popper, used by tooltips).
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

afterEach(() => cleanup());

// jsdom lacks layout APIs that prosemirror-view calls on DOM mutations.
if (typeof document !== "undefined") {
  const emptyRects = () => ({
    length: 0,
    item: () => null,
    [Symbol.iterator]: function* () {},
  });
  const zeroRect = () => ({
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: 0,
    height: 0,
    toJSON() {},
  });
  if (!Range.prototype.getClientRects)
    Range.prototype.getClientRects = emptyRects as never;
  if (!Range.prototype.getBoundingClientRect)
    Range.prototype.getBoundingClientRect = zeroRect as never;
  if (!("getClientRects" in Text.prototype))
    (Text.prototype as unknown as { getClientRects: unknown }).getClientRects =
      emptyRects;
  if (!document.elementFromPoint) document.elementFromPoint = () => null;
}
