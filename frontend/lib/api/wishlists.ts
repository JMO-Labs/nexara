/**
 * @file lib/api/wishlists.ts
 * @brief Wishlists: lists for you or a household member/pet, wishes, and
 *        claims (the owner never sees claims; ``claimed``/``mine`` are null).
 */
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, seg } from "./client";
import type { ProfileLevel } from "@/lib/profile";

export type Occasion =
  | "birthday"
  | "holiday"
  | "school"
  | "wedding"
  | "baby"
  | "custom";

export const OCCASION_LABEL: Record<Occasion, string> = {
  birthday: "Birthday",
  holiday: "Holiday",
  school: "Back to school",
  wedding: "Wedding",
  baby: "Baby",
  custom: "Just because",
};

export interface Wish {
  id: string;
  name: string;
  url: string | null;
  price: string | null;
  notes: string | null;
  qty: number;
  claimed: number | null;
  mine: number | null;
}

export interface Wishlist {
  id: string;
  owner_id: string;
  title: string;
  occasion: Occasion;
  occasion_date: string | null;
  note: string | null;
  visibility: ProfileLevel;
  household: { id: string; name: string; kind: "person" | "pet" } | null;
  item_count: number;
  is_owner: boolean;
}

export interface WishlistDetail extends Wishlist {
  items: Wish[];
}

export interface WishlistInput {
  title?: string;
  occasion?: Occasion;
  occasion_date?: string | null;
  note?: string | null;
  visibility?: ProfileLevel;
  household_id?: string | null;
}

export type WishInput = Partial<
  Pick<Wish, "name" | "url" | "price" | "notes" | "qty">
>;

const B = "/api/v1/wishlists";

export const listWishlists = (
  q: { owner_id?: string; household_id?: string } = {},
) =>
  apiGet<Wishlist[]>(
    `${B}?${new URLSearchParams(q as Record<string, string>)}`,
  );
export const getWishlist = (id: string) =>
  apiGet<WishlistDetail>(`${B}/${seg(id)}`);
export const createWishlist = (body: WishlistInput) =>
  apiPost<WishlistDetail>(B, body);
export const updateWishlist = (id: string, body: WishlistInput) =>
  apiPatch<WishlistDetail>(`${B}/${seg(id)}`, body);
export const deleteWishlist = (id: string) => apiDelete(`${B}/${seg(id)}`);
export const addWish = (id: string, body: WishInput) =>
  apiPost<WishlistDetail>(`${B}/${seg(id)}/items`, body);
export const updateWish = (id: string, itemId: string, body: WishInput) =>
  apiPatch<WishlistDetail>(`${B}/${seg(id)}/items/${seg(itemId)}`, body);
export const deleteWish = (id: string, itemId: string) =>
  apiDelete(`${B}/${seg(id)}/items/${seg(itemId)}`);
export const claimWish = (id: string, itemId: string, qty: number) =>
  apiPut<WishlistDetail>(`${B}/${seg(id)}/items/${seg(itemId)}/claim`, { qty });
export const releaseWish = (id: string, itemId: string) =>
  apiDelete<WishlistDetail>(`${B}/${seg(id)}/items/${seg(itemId)}/claim`);
