/**
 * @file lib/api/tree.ts
 * @brief Family tree and group relationship tree REST client.
 */
import { apiGet, seg } from "./client";

export type TreeNodeKind = "user" | "household" | "private";
export type TreeEdgeKind =
  | "parent"
  | "spouse"
  | "partner"
  | "sibling"
  | "friend"
  | "other"
  | "via_family";

export interface TreeNode {
  /** `u:<uuid>`, `h:<uuid>` or throwaway `p:<n>` for private relatives. */
  id: string;
  name: string;
  avatar_url: string | null;
  kind: TreeNodeKind;
  memorial: boolean;
  link: string | null;
  born: string | null;
  died: string | null;
}

/** `a` -> `b`; for `parent`, a is the parent of b. */
export interface TreeEdge {
  a: string;
  b: string;
  kind: TreeEdgeKind;
}

export interface TreeData {
  nodes: TreeNode[];
  edges: TreeEdge[];
  root: string | null;
  truncated: boolean;
}

/** @brief Relatives around `root` (default: you), `gens` generations each way. */
export const getFamilyTree = (opts: { root?: string; gens?: number } = {}) => {
  const q = new URLSearchParams();
  if (opts.root) q.set("root", opts.root);
  if (opts.gens) q.set("gens", String(opts.gens));
  const s = q.toString();
  return apiGet<TreeData>(`/api/v1/tree/family${s ? `?${s}` : ""}`);
};

/** @brief Relations among the members of a group you belong to. */
export const getGroupTree = (slug: string) =>
  apiGet<TreeData>(`/api/v1/tree/group/${seg(slug)}`);
