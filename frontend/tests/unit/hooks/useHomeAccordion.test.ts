/**
 * @file tests/unit/hooks/useHomeAccordion.test.ts
 * @brief useHomeAccordion: single-open toggle behaviour.
 */
import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useHomeAccordion } from "@/hooks/useHomeAccordion";

describe("useHomeAccordion", () => {
  it("starts with the default open", () => {
    const { result } = renderHook(() => useHomeAccordion("chat"));
    expect(result.current.open).toBe("chat");
  });
  it("closes the open tile when toggled", () => {
    const { result } = renderHook(() => useHomeAccordion("chat"));
    act(() => result.current.toggle("chat"));
    expect(result.current.open).toBeNull();
  });
  it("switches to another tile", () => {
    const { result } = renderHook(() => useHomeAccordion("chat"));
    act(() => result.current.toggle("next"));
    expect(result.current.open).toBe("next");
  });
});
