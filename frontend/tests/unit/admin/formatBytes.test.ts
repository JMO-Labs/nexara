/**
 * @file tests/unit/admin/formatBytes.test.ts
 * @brief Human-readable byte formatting.
 */
import { describe, it, expect } from "vitest";
import { formatBytes } from "@/lib/formatBytes";

describe("formatBytes", () => {
  it("formats small values", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(512)).toBe("512 B");
  });
  it("scales through MB, GB, TB", () => {
    expect(formatBytes(1024 * 1024 * 5)).toBe("5.0 MB");
    expect(formatBytes(1024 ** 3 * 1.5)).toBe("1.5 GB");
    expect(formatBytes(1024 ** 4 * 2)).toBe("2.0 TB");
  });
  it("handles null/negative", () => {
    expect(formatBytes(null)).toBe("0 B");
    expect(formatBytes(-5)).toBe("0 B");
  });
});
