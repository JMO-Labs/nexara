/**
 * @file lib/api/capsules.ts
 * @brief Time capsule REST client. Sealed capsules carry no body/media.
 */
import { apiDelete, apiGet, apiPost, seg } from "./client";

export type RecipientKind = "user" | "subgroup" | "community" | "household";

export interface CapsuleRecipient {
  kind: RecipientKind;
  target_id?: string | null;
}

export interface CapsuleSealed {
  id: string;
  title: string;
  author: { id: string; display_name: string };
  open_at: string;
  recipients_summary: string;
}

export interface CapsuleOpen extends CapsuleSealed {
  body: string;
  media: string[];
  opened_at: string | null;
}

export interface CapsuleList {
  sealed: CapsuleSealed[];
  opened: CapsuleOpen[];
  mine: CapsuleOpen[];
}

export interface CapsuleCreate {
  title: string;
  body: string;
  media_ids: string[];
  open_at: string;
  recipients: CapsuleRecipient[];
}

const BASE = "/api/v1/capsules";

/** @brief Whether a fetched capsule includes its content. */
export const isOpen = (c: CapsuleSealed | CapsuleOpen): c is CapsuleOpen =>
  "body" in c;

export const listCapsules = () => apiGet<CapsuleList>(BASE);
export const getCapsule = (id: string) =>
  apiGet<CapsuleSealed | CapsuleOpen>(`${BASE}/${seg(id)}`);
export const createCapsule = (body: CapsuleCreate) =>
  apiPost<CapsuleOpen>(BASE, body);
export const deleteCapsule = (id: string) => apiDelete(`${BASE}/${seg(id)}`);
