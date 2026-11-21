/**
 * @file tests/unit/stores/homeScope.test.ts
 * @brief homeScope store and inScope helper.
 */
import { describe, it, expect } from "vitest";
import { inScope, useHomeScope } from "@/stores/homeScope";

describe("inScope", () => {
  it("rejects null group for a specific scope", () => {
    expect(inScope(null, "x")).toBe(false);
  });
  it("accepts everything for all", () => {
    expect(inScope("x", "all")).toBe(true);
    expect(inScope(null, "all")).toBe(true);
  });
  it("matches equal ids", () => {
    expect(inScope("x", "x")).toBe(true);
    expect(inScope("y", "x")).toBe(false);
  });
});

describe("useHomeScope", () => {
  it("defaults to all and updates", () => {
    expect(useHomeScope.getState().scope).toBe("all");
    useHomeScope.getState().setScope("g1");
    expect(useHomeScope.getState().scope).toBe("g1");
    useHomeScope.getState().setScope("all");
  });
});
