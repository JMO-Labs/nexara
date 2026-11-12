/**
 * @file tests/unit/hooks/useIsMobile.test.ts
 * @brief useIsMobile follows a mocked matchMedia and its change events.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useIsMobile } from "@/hooks/useIsMobile";

function mockMatchMedia(matches: boolean) {
  const listeners = new Set<(e: MediaQueryListEvent) => void>();
  const mq = {
    matches,
    addEventListener: vi.fn((_: string, l: (e: MediaQueryListEvent) => void) =>
      listeners.add(l),
    ),
    removeEventListener: vi.fn(
      (_: string, l: (e: MediaQueryListEvent) => void) => listeners.delete(l),
    ),
  };
  const fn = vi.fn().mockReturnValue(mq);
  vi.stubGlobal("matchMedia", fn);
  window.matchMedia = fn as never;
  return {
    mq,
    fn,
    emit: (m: boolean) =>
      listeners.forEach((l) => l({ matches: m } as MediaQueryListEvent)),
  };
}

describe("useIsMobile", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns true when the query matches", () => {
    const { fn } = mockMatchMedia(true);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(true);
    expect(fn).toHaveBeenCalledWith("(max-width: 767px)");
  });

  it("returns false when the query does not match", () => {
    mockMatchMedia(false);
    const { result } = renderHook(() => useIsMobile());
    expect(result.current).toBe(false);
  });

  it("reacts to change events", () => {
    const { emit } = mockMatchMedia(false);
    const { result } = renderHook(() => useIsMobile());
    act(() => emit(true));
    expect(result.current).toBe(true);
    act(() => emit(false));
    expect(result.current).toBe(false);
  });

  it("removes its listener on unmount", () => {
    const { mq } = mockMatchMedia(false);
    const { unmount } = renderHook(() => useIsMobile());
    unmount();
    expect(mq.removeEventListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function),
    );
  });
});
