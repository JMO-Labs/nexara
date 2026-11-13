import { describe, it, expect } from "vitest";
import {
  reorder,
  validateTemplate,
  type TemplateField,
} from "@/lib/lists/templateModel";

const f = (id: string, over: Partial<TemplateField> = {}): TemplateField => ({
  id,
  key: id,
  label: id.toUpperCase(),
  type_key: "text",
  config: {},
  position: 0,
  ...over,
});

describe("reorder", () => {
  it("moves item and rewrites positions", () => {
    const out = reorder([f("a"), f("b"), f("c")], "a", "c");
    expect(out.map((x) => x.id)).toEqual(["b", "c", "a"]);
    expect(out.map((x) => x.position)).toEqual([0, 1, 2]);
  });
  it("is a no-op for unknown ids", () => {
    expect(reorder([f("a"), f("b")], "a", "zzz").map((x) => x.id)).toEqual([
      "a",
      "b",
    ]);
  });
});

describe("validateTemplate", () => {
  it("accepts valid fields", () => {
    expect(validateTemplate("T", [f("a")])).toEqual({ fields: {} });
  });
  it("requires a template name", () => {
    expect(validateTemplate(" ", [f("a")]).name).toBeTruthy();
  });
  it("flags empty labels", () => {
    expect(validateTemplate("T", [f("a", { label: " " })]).fields.a).toMatch(
      /label/i,
    );
  });
  it("flags unknown types", () => {
    expect(
      validateTemplate("T", [f("a", { type_key: "nope" })]).fields.a,
    ).toBeTruthy();
  });
  it("select needs options with values", () => {
    const bad = f("a", { type_key: "select", config: { options: [] } });
    expect(validateTemplate("T", [bad]).fields.a).toMatch(/option/i);
    const ok = f("a", {
      type_key: "select",
      config: { options: [{ value: "x", label: "X" }] },
    });
    expect(validateTemplate("T", [ok])).toEqual({ fields: {} });
  });
  it("keeps a field id of 'name' separate from the name error", () => {
    const r = validateTemplate(" ", [f("name", { label: "" })]);
    expect(r.name).toMatch(/name/i);
    expect(r.fields.name).toMatch(/label/i);
  });
  it("rejects duplicate field keys", () => {
    const r = validateTemplate("T", [
      f("a", { key: "k" }),
      f("b", { key: "k" }),
    ]);
    expect(r.fields.b).toMatch(/unique|duplicate/i);
    expect(r.fields.a).toBeUndefined();
  });
});
