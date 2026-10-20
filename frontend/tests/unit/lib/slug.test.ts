import { describe, it, expect } from "vitest";
import { slugify, isValidSlugFormat } from "@/lib/slug";

describe("slugify", () => {
  it("converts spaces to dashes", () => {
    expect(slugify("hello world")).toBe("hello-world");
  });

  it("lowercases the input", () => {
    expect(slugify("HELLO World")).toBe("hello-world");
  });

  it("strips special characters", () => {
    expect(slugify("hello@world!")).toBe("hello-world");
  });

  it("drops leading dashes and underscores", () => {
    expect(slugify("-_hello")).toBe("hello");
  });

  it("drops trailing dashes", () => {
    expect(slugify("hello-")).toBe("hello");
  });

  it("collapses multiple dashes", () => {
    expect(slugify("hello---world")).toBe("hello-world");
  });

  it("is idempotent on already-valid input", () => {
    const valid = "hello-world-123";
    expect(slugify(valid)).toBe(valid);
  });

  it("returns empty string for empty input", () => {
    expect(slugify("")).toBe("");
  });

  it("handles leading symbols only", () => {
    expect(slugify("-hello-world")).toBe("hello-world");
  });

  it("handles complex mixed case with spaces and special chars", () => {
    expect(slugify("My Cool Group!!!")).toBe("my-cool-group");
  });
});

describe("isValidSlugFormat", () => {
  it("accepts valid slugs starting with letter", () => {
    expect(isValidSlugFormat("hello")).toBe(true);
  });

  it("accepts valid slugs starting with number", () => {
    expect(isValidSlugFormat("123-hello")).toBe(true);
  });

  it("accepts dashes and underscores in middle", () => {
    expect(isValidSlugFormat("hello-world_123")).toBe(true);
  });

  it("rejects empty string", () => {
    expect(isValidSlugFormat("")).toBe(false);
  });

  it("rejects slugs starting with dash", () => {
    expect(isValidSlugFormat("-hello")).toBe(false);
  });

  it("rejects slugs starting with underscore", () => {
    expect(isValidSlugFormat("_hello")).toBe(false);
  });

  it("rejects slugs with spaces", () => {
    expect(isValidSlugFormat("hello world")).toBe(false);
  });

  it("rejects slugs with uppercase", () => {
    expect(isValidSlugFormat("Hello")).toBe(false);
  });

  it("rejects slugs with special characters", () => {
    expect(isValidSlugFormat("hello@world")).toBe(false);
  });
});
