/**
 * @file tests/unit/lib/patterns.test.ts
 * @brief patternUrl generators.
 */
import { describe, it, expect } from "vitest";
import { PATTERNS, patternUrl } from "@/lib/patterns";

describe("patternUrl", () => {
  it("returns null for none", () => {
    expect(patternUrl("none")).toBeNull();
  });
  it.each(PATTERNS.filter((p) => p !== "none"))(
    "%s is an svg data url",
    (p) => {
      expect(patternUrl(p)).toMatch(/^url\("data:image\/svg\+xml,/);
    },
  );
  it("contour is deterministic", () => {
    expect(patternUrl("contour")).toBe(patternUrl("contour"));
  });
});
