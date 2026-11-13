/**
 * @file tests/unit/lib/customCss.test.ts
 * @brief Unit tests for custom CSS size helpers.
 */
import { describe, it, expect } from "vitest";
import { MAX_CSS_BYTES, cssByteLength } from "@/lib/customCss";

describe("cssByteLength", () => {
  it("counts UTF-8 bytes, not chars", () => {
    expect(cssByteLength("abc")).toBe(3);
    expect(cssByteLength("é")).toBe(2);
  });

  it("mirrors the backend limit", () => {
    expect(MAX_CSS_BYTES).toBe(10240);
  });
});
