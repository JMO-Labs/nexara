/**
 * @file lib/tree/outline.ts
 * @brief Nested-list form of a tree for screen readers: each person once,
 *        children under their parent, partners and friends as text.
 */
import type { TreeEdge, TreeNode } from "@/lib/api/tree";

export interface OutlineItem {
  node: TreeNode;
  /** Plain phrases such as "partner of Sam". */
  notes: string[];
  children: OutlineItem[];
}

/** @brief Dates for a remembered person, e.g. "1930 to 2020". */
export function lifespan(n: TreeNode): string | null {
  if (!n.memorial || (!n.born && !n.died)) return null;
  const y = (d: string | null) => (d ? d.slice(0, 4) : "?");
  return `${y(n.born)} to ${y(n.died)}`;
}

const NOTE: Record<string, string> = {
  spouse: "married to",
  partner: "partner of",
  sibling: "sibling of",
  friend: "friend of",
  other: "linked to",
  via_family: "related via family to",
};

/**
 * @param nodes people
 * @param edges relations
 * @param showFriends include friend/other notes
 * @return top-level items (people without parents first), sorted by name
 */
export function buildOutline(
  nodes: TreeNode[],
  edges: TreeEdge[],
  showFriends: boolean,
): OutlineItem[] {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const sort = (ids: string[]) =>
    ids.sort((x, y) =>
      byId.get(x)!.name === byId.get(y)!.name
        ? x < y
          ? -1
          : 1
        : byId.get(x)!.name < byId.get(y)!.name
          ? -1
          : 1,
    );
  const kids = new Map<string, string[]>();
  const hasParent = new Set<string>();
  const notes = new Map<string, string[]>();
  for (const e of edges) {
    if (!byId.has(e.a) || !byId.has(e.b)) continue;
    if (e.kind === "parent") {
      kids.set(e.a, [...(kids.get(e.a) ?? []), e.b]);
      hasParent.add(e.b);
    } else if (showFriends || (e.kind !== "friend" && e.kind !== "other")) {
      const add = (from: string, to: string) =>
        notes.set(from, [
          ...(notes.get(from) ?? []),
          `${NOTE[e.kind] ?? "linked to"} ${byId.get(to)!.name}`,
        ]);
      add(e.a, e.b);
      add(e.b, e.a);
    }
  }
  const seen = new Set<string>();
  const visit = (id: string): OutlineItem => {
    seen.add(id);
    const children = sort([...new Set(kids.get(id) ?? [])])
      .filter((c) => !seen.has(c))
      .map(visit);
    return {
      node: byId.get(id)!,
      notes: (notes.get(id) ?? []).sort(),
      children,
    };
  };
  const out: OutlineItem[] = [];
  for (const id of sort(
    nodes.map((n) => n.id).filter((i) => !hasParent.has(i)),
  ))
    if (!seen.has(id)) out.push(visit(id));
  for (const id of sort(nodes.map((n) => n.id)))
    if (!seen.has(id)) out.push(visit(id));
  return out;
}
