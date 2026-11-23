/**
 * @file lib/tree/layout.ts
 * @brief Deterministic generational tree layout (pure, no DOM).
 *        Generation = longest parent chain; spouses, partners and siblings
 *        share a row; rows ordered by one barycenter pass; disconnected
 *        families sit side by side; unlinked nodes are returned in `loose`.
 */

export const NODE_W = 144;
export const NODE_H = 56;
export const GAP_X = 24;
export const GAP_Y = 72;
export const COMP_GAP = 48;

export interface LayoutNode {
  id: string;
}
export interface LayoutEdge {
  a: string;
  b: string;
  kind: string;
}
export interface LayoutOptions {
  showFriends: boolean;
}
export interface LayoutResult {
  /** Top-left corner of each placed node. */
  positions: Record<string, { x: number; y: number }>;
  width: number;
  height: number;
  /** Nodes with no visible link, left out of `positions`. */
  loose: string[];
}

const SAME_ROW = new Set(["spouse", "partner", "sibling"]);
const STRUCTURAL = new Set(["parent", ...SAME_ROW]);
const SOFT = new Set(["friend", "other"]);

/** @brief Edges the layout should consider. */
export function activeEdges<E extends LayoutEdge>(
  edges: E[],
  showFriends: boolean,
): E[] {
  return edges.filter(
    (e) =>
      STRUCTURAL.has(e.kind) ||
      e.kind === "via_family" ||
      (showFriends && SOFT.has(e.kind)),
  );
}

function components(ids: string[], edges: LayoutEdge[]): string[][] {
  const parent = new Map(ids.map((i) => [i, i]));
  const find = (x: string): string => {
    let r = x;
    while (parent.get(r) !== r) r = parent.get(r)!;
    parent.set(x, r);
    return r;
  };
  for (const e of edges) {
    if (!STRUCTURAL.has(e.kind)) continue;
    const ra = find(e.a);
    const rb = find(e.b);
    if (ra !== rb) parent.set(ra < rb ? rb : ra, ra < rb ? ra : rb);
  }
  const groups = new Map<string, string[]>();
  for (const id of ids) {
    const r = find(id);
    groups.set(r, [...(groups.get(r) ?? []), id]);
  }
  return [...groups.values()]
    .map((g) => g.sort())
    .sort((x, y) => (x[0] < y[0] ? -1 : 1));
}

function generations(ids: string[], edges: LayoutEdge[]): Map<string, number> {
  const gen = new Map(ids.map((i) => [i, 0]));
  for (let pass = 0; pass <= ids.length; pass++) {
    let changed = false;
    for (const e of edges) {
      if (!gen.has(e.a) || !gen.has(e.b)) continue;
      const ga = gen.get(e.a)!;
      const gb = gen.get(e.b)!;
      if (e.kind === "parent" && gb < ga + 1) {
        gen.set(e.b, ga + 1);
        changed = true;
      } else if (SAME_ROW.has(e.kind) && ga !== gb) {
        gen.set(e.a, Math.max(ga, gb));
        gen.set(e.b, Math.max(ga, gb));
        changed = true;
      }
    }
    if (!changed) break;
  }
  return gen;
}

/** Spouse/partner units on one row: linked people stay adjacent. */
function units(row: string[], edges: LayoutEdge[]): string[][] {
  const set = new Set(row);
  const next = new Map(row.map((i) => [i, [i]]));
  for (const e of edges) {
    if (
      (e.kind !== "spouse" && e.kind !== "partner") ||
      !set.has(e.a) ||
      !set.has(e.b)
    )
      continue;
    const ua = next.get(e.a)!;
    const ub = next.get(e.b)!;
    if (ua === ub) continue;
    const merged = [...ua, ...ub].sort();
    merged.forEach((m) => next.set(m, merged));
  }
  return [...new Set(next.values())].sort((x, y) => (x[0] < y[0] ? -1 : 1));
}

function placeComponent(
  ids: string[],
  edges: LayoutEdge[],
  originX: number,
  out: Record<string, { x: number; y: number }>,
): { width: number; rows: number } {
  const gen = generations(ids, edges);
  const maxGen = Math.max(...gen.values());
  const parents = new Map<string, string[]>();
  for (const e of edges)
    if (e.kind === "parent" && gen.has(e.a) && gen.has(e.b))
      parents.set(e.b, [...(parents.get(e.b) ?? []), e.a]);
  const rows: string[][] = [];
  for (let g = 0; g <= maxGen; g++)
    rows.push(ids.filter((i) => gen.get(i) === g));
  const rowWidth = (n: number) => n * NODE_W + Math.max(0, n - 1) * GAP_X;
  const width = Math.max(...rows.map((r) => rowWidth(r.length)));
  const cx = new Map<string, number>();
  rows.forEach((row, g) => {
    const bary = (u: string[]) => {
      const xs = u
        .flatMap((m) => (parents.get(m) ?? []).map((p) => cx.get(p)!))
        .filter((x) => x !== undefined);
      return xs.length ? xs.reduce((s, x) => s + x, 0) / xs.length : Infinity;
    };
    const ordered = units(row, edges)
      .map((u) => ({ u, b: bary(u) }))
      .sort((p, q) => (p.b === q.b ? (p.u[0] < q.u[0] ? -1 : 1) : p.b - q.b))
      .flatMap((p) => p.u);
    let x = originX + (width - rowWidth(ordered.length)) / 2;
    for (const id of ordered) {
      out[id] = { x, y: g * (NODE_H + GAP_Y) };
      cx.set(id, x + NODE_W / 2);
      x += NODE_W + GAP_X;
    }
  });
  return { width, rows: rows.length };
}

/**
 * @brief Compute node positions.
 * @param nodes people
 * @param edges relations (parent edges point parent -> child)
 * @param opts `showFriends` includes friend/other links
 * @return positions, overall size and unlinked ids
 */
export function layoutTree(
  nodes: LayoutNode[],
  edges: LayoutEdge[],
  opts: LayoutOptions,
): LayoutResult {
  const ids = nodes.map((n) => n.id);
  const known = new Set(ids);
  const live = activeEdges(edges, opts.showFriends).filter(
    (e) => known.has(e.a) && known.has(e.b),
  );
  const linked = new Set(live.flatMap((e) => [e.a, e.b]));
  const loose = ids.filter((i) => !linked.has(i)).sort();
  const positions: Record<string, { x: number; y: number }> = {};
  let x = 0;
  let maxRows = 0;
  for (const comp of components([...linked].sort(), live)) {
    const set = new Set(comp);
    const { width, rows } = placeComponent(
      comp,
      live.filter((e) => set.has(e.a)),
      x,
      positions,
    );
    x += width + COMP_GAP;
    maxRows = Math.max(maxRows, rows);
  }
  const width = Math.max(0, x - COMP_GAP);
  const height = maxRows ? maxRows * NODE_H + (maxRows - 1) * GAP_Y : 0;
  return { positions, width, height, loose };
}
