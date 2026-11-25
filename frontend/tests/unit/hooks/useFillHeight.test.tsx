/**
 * @file tests/unit/hooks/useFillHeight.test.tsx
 * @brief Fill-height hook: offset math and live CSS variable updates.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, act } from "@testing-library/react";
import * as React from "react";
import { docTop, fillHeight, useFillHeight } from "@/hooks/useFillHeight";

/** @brief Stub layout offsets on an element. */
function place(el: HTMLElement, top: number, parent: Element | null = null) {
  Object.defineProperty(el, "offsetTop", { configurable: true, value: top });
  Object.defineProperty(el, "offsetParent", {
    configurable: true,
    value: parent,
  });
}

function Probe({ gap }: { gap?: number }) {
  const ref = React.useRef<HTMLDivElement>(null);
  useFillHeight(ref, "--bento-h", gap);
  return <div ref={ref} data-testid="probe" />;
}

describe("fillHeight", () => {
  it("is viewport minus top minus gap", () => {
    expect(fillHeight(250, 900, 24)).toBe(626);
  });
  it("floors fractional px and never goes negative", () => {
    expect(fillHeight(100.6, 900.4, 0)).toBe(799);
    expect(fillHeight(1000, 700, 24)).toBe(0);
  });
});

describe("docTop", () => {
  it("sums offsetTop up the offsetParent chain (ignores transforms)", () => {
    const outer = document.createElement("div");
    const inner = document.createElement("div");
    place(outer, 80);
    place(inner, 170, outer);
    expect(docTop(inner)).toBe(250);
  });
});

describe("useFillHeight", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sets the variable and re-measures on resize", () => {
    vi.stubGlobal("innerHeight", 900);
    const { getByTestId } = render(<Probe gap={24} />);
    const el = getByTestId("probe");
    place(el, 250);
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });
    expect(el.style.getPropertyValue("--bento-h")).toBe("626px");
    vi.stubGlobal("innerHeight", 700);
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });
    expect(el.style.getPropertyValue("--bento-h")).toBe("426px");
  });
});
