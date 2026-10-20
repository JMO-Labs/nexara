/**
 * @file tests/unit/lib/widgets/registry.test.ts
 * @brief Unit tests for the widget registry module.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  register,
  getDef,
  listDefs,
  clearRegistry,
  type WidgetDef,
} from "@/lib/widgets/registry";
import React from "react";

const _noop = () => React.createElement("div");

function makeDef(
  id: string,
  category: WidgetDef["category"] = "core",
  title = id,
): WidgetDef {
  return {
    id,
    title,
    defaultSize: 4,
    category,
    Component: _noop,
  };
}

describe("widget registry", () => {
  beforeEach(() => {
    clearRegistry();
  });

  it("register adds def; listDefs returns it", () => {
    const def = makeDef("feed");
    register(def);
    const defs = listDefs();
    expect(defs).toHaveLength(1);
    expect(defs[0].id).toBe("feed");
  });

  it("duplicate id with same component is a no-op (no throw)", () => {
    const def = makeDef("feed");
    register(def);
    // Same id + same Component reference — must not throw.
    expect(() => register(def)).not.toThrow();
    // Still only one entry.
    expect(listDefs()).toHaveLength(1);
  });

  it("duplicate id with different component warns and overwrites", () => {
    const warnSpy = vi
      .spyOn(console, "warn")
      .mockImplementation(() => undefined);
    const def1 = makeDef("feed");
    const def2 = {
      ...makeDef("feed"),
      Component: () => React.createElement("span"),
    };
    register(def1);
    register(def2);
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringMatching(/re-registered/),
    );
    expect(getDef("feed")).toBe(def2);
    warnSpy.mockRestore();
  });

  it("getDef returns def when found", () => {
    const def = makeDef("feed");
    register(def);
    expect(getDef("feed")).toBe(def);
  });

  it("getDef returns undefined when not found", () => {
    expect(getDef("nonexistent")).toBeUndefined();
  });

  it("clearRegistry empties all registrations", () => {
    register(makeDef("feed"));
    register(makeDef("activity"));
    clearRegistry();
    expect(listDefs()).toHaveLength(0);
    expect(getDef("feed")).toBeUndefined();
  });

  it("listDefs sorts by category then title", () => {
    register(makeDef("z-widget", "social", "Zzz"));
    register(makeDef("a-widget", "core", "Aaa"));
    register(makeDef("m-widget", "media", "Mmm"));
    register(makeDef("b-widget", "core", "Bbb"));

    const defs = listDefs();
    expect(defs.map((d) => d.id)).toEqual([
      "a-widget",
      "b-widget",
      "m-widget",
      "z-widget",
    ]);
  });
});
