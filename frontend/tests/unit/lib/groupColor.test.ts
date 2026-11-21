/**
 * @file tests/unit/lib/groupColor.test.ts
 * @brief groupColor: accent passthrough, null fallback, stable palette pick.
 */
import { describe, it, expect } from "vitest";
import { groupColor, GROUP_PALETTE } from "@/lib/groupColor";

describe("groupColor", () => {
  it("returns blue token for null id", () => {
    expect(groupColor(null)).toBe("var(--nx-blue)");
  });
  it("prefers accent", () => {
    expect(groupColor("abc", "#123456")).toBe("#123456");
  });
  it("is stable and in palette", () => {
    expect(groupColor("abc")).toBe(groupColor("abc"));
    expect(GROUP_PALETTE).toContain(groupColor("abc"));
    expect(groupColor("abc")).toBe(GROUP_PALETTE[(97 + 98 + 99) % 6]);
  });
});
