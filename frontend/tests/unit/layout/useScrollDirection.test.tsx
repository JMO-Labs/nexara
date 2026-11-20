/**
 * @file tests/unit/layout/useScrollDirection.test.tsx
 * @brief Scroll direction hook.
 */
import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useScrollDirection } from "@/hooks/useScrollDirection";

function scrollTo(y: number) {
  act(() => {
    Object.defineProperty(window, "scrollY", { value: y, configurable: true });
    window.dispatchEvent(new Event("scroll"));
  });
}

describe("useScrollDirection", () => {
  it("is down past the threshold and up when scrolling back", () => {
    const { result } = renderHook(() => useScrollDirection(80));
    expect(result.current).toBe("up");
    scrollTo(50);
    expect(result.current).toBe("up");
    scrollTo(200);
    expect(result.current).toBe("down");
    scrollTo(150);
    expect(result.current).toBe("up");
  });
});
