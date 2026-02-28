/**
 * @file tests/smoke.test.ts
 * @brief Smoke test to verify Vitest is configured correctly.
 */

import { describe, it, expect } from "vitest";

describe("vitest setup", () => {
  it("runs a basic test", () => {
    expect(1 + 1).toBe(2);
  });

  it("has access to happy-dom environment", () => {
    expect(typeof document).toBe("object");
    expect(typeof window).toBe("object");
  });
});
