/**
 * @file tests/unit/lib/cssHighlight.test.ts
 * @brief CSS tokenizer used by the admin CSS editor.
 */
import { describe, it, expect } from "vitest";
import { tokenizeCss, cssByteLength } from "@/lib/cssHighlight";

describe("tokenizeCss", () => {
  it("round-trips the source text", () => {
    const src = "/* c */\n@media (x) { a:hover { color: #fff; } }";
    expect(
      tokenizeCss(src)
        .map((t) => t.text)
        .join(""),
    ).toBe(src);
  });

  it("classifies selectors, properties, values and comments", () => {
    const toks = tokenizeCss("h1 { color: #ff0000; margin: 2px } /* x */");
    const of = (type: string) =>
      toks.filter((t) => t.type === type).map((t) => t.text);
    expect(of("selector")).toContain("h1");
    expect(of("property")).toEqual(["color", "margin"]);
    expect(of("value")).toEqual(expect.arrayContaining(["#ff0000", "2px"]));
    expect(of("comment")).toEqual(["/* x */"]);
  });

  it("treats pseudo-class selectors as selectors", () => {
    const toks = tokenizeCss("a:hover { top: 0 }");
    expect(toks.find((t) => t.text === "a")?.type).toBe("selector");
    expect(toks.find((t) => t.text === "top")?.type).toBe("property");
  });

  it("marks at-rules", () => {
    expect(tokenizeCss("@media print {}")[0]).toEqual({
      type: "atrule",
      text: "@media",
    });
  });
});

describe("cssByteLength", () => {
  it("counts UTF-8 bytes, not chars", () => {
    expect(cssByteLength("abc")).toBe(3);
    expect(cssByteLength("é")).toBe(2);
  });
});
