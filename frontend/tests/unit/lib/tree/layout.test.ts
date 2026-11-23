/**
 * @file tests/unit/lib/tree/layout.test.ts
 * @brief Deterministic tree layout rules.
 */
import { describe, expect, it } from "vitest";
import { NODE_W, layoutTree } from "@/lib/tree/layout";

const n = (...ids: string[]) => ids.map((id) => ({ id }));
const e = (a: string, b: string, kind = "parent") => ({ a, b, kind });
const opts = { showFriends: true };

describe("layoutTree", () => {
  it("puts grandparent above parent above child", () => {
    const r = layoutTree(n("c", "g", "p"), [e("g", "p"), e("p", "c")], opts);
    expect(r.positions.g.y).toBeLessThan(r.positions.p.y);
    expect(r.positions.p.y).toBeLessThan(r.positions.c.y);
  });

  it("keeps spouses on one row, adjacent", () => {
    const r = layoutTree(
      n("a", "b", "c", "k"),
      [e("a", "k"), e("b", "k"), e("a", "b", "spouse"), e("c", "k", "friend")],
      opts,
    );
    expect(r.positions.a.y).toBe(r.positions.b.y);
    expect(Math.abs(r.positions.a.x - r.positions.b.x)).toBeLessThan(
      NODE_W * 2,
    );
  });

  it("lifts a spouse who has no parents to the partner's generation", () => {
    const r = layoutTree(
      n("g", "p", "s", "c"),
      [e("g", "p"), e("p", "s", "spouse"), e("p", "c"), e("s", "c")],
      opts,
    );
    expect(r.positions.s.y).toBe(r.positions.p.y);
    expect(r.positions.c.y).toBeGreaterThan(r.positions.p.y);
  });

  it("does not overlap two disconnected families", () => {
    const r = layoutTree(
      n("a", "b", "x", "y"),
      [e("a", "b"), e("x", "y")],
      opts,
    );
    const boxes = Object.values(r.positions);
    for (const p of boxes)
      for (const q of boxes)
        if (p !== q && p.y === q.y)
          expect(Math.abs(p.x - q.x)).toBeGreaterThanOrEqual(NODE_W);
  });

  it("excludes friend edges when showFriends is false", () => {
    const edges = [e("a", "b"), e("a", "f", "friend")];
    const off = layoutTree(n("a", "b", "f"), edges, { showFriends: false });
    expect(off.loose).toEqual(["f"]);
    expect(off.positions.f).toBeUndefined();
    const on = layoutTree(n("a", "b", "f"), edges, opts);
    expect(on.loose).toEqual([]);
    expect(on.positions.f).toBeDefined();
  });

  it("returns unlinked nodes as loose", () => {
    const r = layoutTree(n("a", "b", "z"), [e("a", "b")], opts);
    expect(r.loose).toEqual(["z"]);
  });

  it("is deterministic regardless of input order", () => {
    const edges = [
      e("a", "c"),
      e("b", "c"),
      e("a", "d"),
      e("a", "b", "spouse"),
    ];
    const one = layoutTree(n("a", "b", "c", "d"), edges, opts);
    const two = layoutTree(n("d", "c", "b", "a"), [...edges].reverse(), opts);
    expect(two).toEqual(one);
  });

  it("survives a parent cycle", () => {
    const r = layoutTree(n("a", "b"), [e("a", "b"), e("b", "a")], opts);
    expect(Object.keys(r.positions)).toHaveLength(2);
  });
});
