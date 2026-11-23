/**
 * @file lib/api/relations.ts
 * @brief Relations REST client: request, confirm, remove, list.
 */
import { apiDelete, apiGet, apiPost, seg } from "./client";

export type RelationKind =
  | "parent"
  | "child"
  | "spouse"
  | "partner"
  | "sibling"
  | "friend"
  | "other";

export interface RelationPerson {
  id: string;
  type: "user" | "household";
  name: string;
  username: string | null;
  avatar_url: string | null;
  memorial: boolean;
}

/** One relation seen from the profile owner: `person` is `kind` of them. */
export interface Relation {
  id: string;
  status: "pending" | "confirmed";
  kind: RelationKind;
  label: string | null;
  /** Plain-language word, e.g. "mother". */
  display: string;
  direction: "incoming" | "outgoing" | null;
  person: RelationPerson;
}

export interface RelationCreate {
  to_user_id?: string;
  to_member_id?: string;
  /** What the other person is to you ("Ruth is my parent"). */
  kind: RelationKind;
  label?: string;
}

const BASE = "/api/v1/relations";

export const listRelations = (userId?: string) =>
  apiGet<Relation[]>(userId ? `${BASE}?user_id=${seg(userId)}` : BASE);
export const listRelationRequests = () =>
  apiGet<Relation[]>(`${BASE}/requests`);
export const requestRelation = (body: RelationCreate) =>
  apiPost<Relation>(BASE, body);
export const confirmRelation = (id: string) =>
  apiPost<{ message: string }>(`${BASE}/${seg(id)}/confirm`);
export const removeRelation = (id: string) => apiDelete(`${BASE}/${seg(id)}`);
