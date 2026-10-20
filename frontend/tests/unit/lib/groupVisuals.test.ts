/**
 * @file tests/unit/lib/groupVisuals.test.ts
 * @brief Test utility functions for group visual identity (hash, gradient, monogram).
 */
import { describe, it, expect } from "vitest";
import { hashSlug, gradientFor, monogram } from "@/lib/groupVisuals";

describe("groupVisuals", () => {
  describe("hashSlug", () => {
    it("returns a deterministic 32-bit unsigned integer for the same slug", () => {
      const hash1 = hashSlug("engineering");
      const hash2 = hashSlug("engineering");
      expect(hash1).toBe(hash2);
      expect(typeof hash1).toBe("number");
      expect(hash1).toBeGreaterThanOrEqual(0);
      expect(hash1).toBeLessThanOrEqual(0xffffffff);
    });

    it("returns different hashes for different slugs", () => {
      const hash1 = hashSlug("engineering");
      const hash2 = hashSlug("marketing");
      expect(hash1).not.toBe(hash2);
    });

    it("handles empty string", () => {
      const hash = hashSlug("");
      expect(typeof hash).toBe("number");
      expect(hash).toBeGreaterThanOrEqual(0);
    });
  });

  describe("gradientFor", () => {
    it("returns an object with background and monogramBg properties", () => {
      const result = gradientFor("engineering");
      expect(result).toHaveProperty("background");
      expect(result).toHaveProperty("monogramBg");
      expect(typeof result.background).toBe("string");
      expect(typeof result.monogramBg).toBe("string");
    });

    it("generates deterministic gradients for the same slug", () => {
      const grad1 = gradientFor("engineering");
      const grad2 = gradientFor("engineering");
      expect(grad1).toEqual(grad2);
    });

    it("background contains linear-gradient with hsl colors", () => {
      const result = gradientFor("test");
      expect(result.background).toContain("linear-gradient");
      expect(result.background).toContain("hsl(");
    });

    it("monogramBg contains hsl color", () => {
      const result = gradientFor("test");
      expect(result.monogramBg).toContain("hsl(");
    });

    it('uses "group" as fallback when slug is empty string', () => {
      const empty = gradientFor("");
      const group = gradientFor("group");
      expect(empty).toEqual(group);
    });

    it('uses "group" as fallback when slug is null/undefined-like', () => {
      const nullGrad = gradientFor("");
      expect(nullGrad.background).toBeDefined();
      expect(nullGrad.monogramBg).toBeDefined();
    });
  });

  describe("monogram", () => {
    it("returns first two chars of single-word name in uppercase", () => {
      expect(monogram("engineering")).toBe("EN");
    });

    it("returns first letter of first and last word for multi-word names", () => {
      expect(monogram("Engineering Team")).toBe("ET");
      expect(monogram("Product Management Group")).toBe("PG");
    });

    it("handles more than two words by taking first and last", () => {
      expect(monogram("Product Management Working Group")).toBe("PG");
    });

    it("handles whitespace by trimming and splitting on any whitespace", () => {
      expect(monogram("  Engineering  ")).toBe("EN");
      expect(monogram("Product    Team")).toBe("PT");
    });

    it("returns middle dot for empty/whitespace-only string", () => {
      expect(monogram("")).toBe("·");
      expect(monogram("   ")).toBe("·");
    });

    it("handles single character words", () => {
      expect(monogram("A B")).toBe("AB");
    });

    it("caps at two characters", () => {
      expect(monogram("abc")).toBe("AB");
    });
  });
});
