/**
 * @file lib/api/wishlists.ts
 * @brief Wishlists for anyone: recipients, money (integer cents), dates,
 *        registries, gifts and cash funds, claims. ``claimed``/``mine``/
 *        ``claimers`` are null when claims are hidden from the viewer.
 */
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, seg } from "./client";
import type { ProfileLevel } from "@/lib/profile";
import type { Occasion } from "@/lib/occasions";

export type { Occasion } from "@/lib/occasions";

export type RecipientKind =
  | "user"
  | "household"
  | "subgroup"
  | "name"
  | "everyone";

export interface RecipientIn {
  kind: RecipientKind;
  ref_id?: string | null;
  name?: string | null;
}

export interface Recipient extends RecipientIn {
  name: string;
  /** Household kind ("pet"/"person") or group slug. */
  extra: string | null;
}

export interface RegistryLink {
  label: string;
  url: string;
}

export interface Wish {
  id: string;
  kind: "gift" | "fund";
  name: string;
  url: string | null;
  price_cents: number | null;
  goal_cents: number | null;
  notes: string | null;
  qty: number;
  claimed: number | null;
  mine: number | null;
  claimers:
    | {
        user_id: string;
        name: string;
        qty: number;
        amount_cents: number | null;
      }[]
    | null;
  /** Buy link: shop's own, tagged Amazon link, or the url. */
  link?: string | null;
  preview: {
    id: string;
    title: string | null;
    site_name: string | null;
    has_image: boolean;
    price_cents: number | null;
    currency: string | null;
    /** Link to buy through (Amazon's partner-tagged page); use as-is. */
    buy_url: string | null;
    checked_at: string | null;
  } | null;
  /** Price follows the shop until someone types their own. */
  price_auto: boolean;
}

export interface Wishlist {
  id: string;
  owner_id: string;
  owner_name: string;
  title: string;
  occasion: Occasion;
  occasion_label: string | null;
  event_date: string | null;
  due_by: string | null;
  note: string | null;
  visibility: ProfileLevel;
  currency: string;
  budget_min_cents: number | null;
  budget_max_cents: number | null;
  event_budget_cents: number | null;
  giver_cap_cents: number | null;
  hide_claims: boolean;
  registry_links: RegistryLink[];
  recipients: Recipient[];
  item_count: number;
  is_owner: boolean;
  can_edit_items: boolean;
  sees_claims: boolean;
}

/** @brief Where gifts go; address null = that person stopped sharing it. */
export interface ShipTo {
  user_id: string | null;
  event_id: string | null;
  starts_at: string | null;
  name: string | null;
  address: string | null;
}

export interface WishlistDetail extends Wishlist {
  items: Wish[];
  ship_to: ShipTo | null;
  planned_cents: number | null;
  my_total_cents: number;
}

export interface WishlistInput {
  title?: string;
  occasion?: Occasion;
  occasion_label?: string | null;
  event_date?: string | null;
  due_by?: string | null;
  note?: string | null;
  visibility?: ProfileLevel;
  currency?: string;
  budget_min_cents?: number | null;
  budget_max_cents?: number | null;
  event_budget_cents?: number | null;
  giver_cap_cents?: number | null;
  hide_claims?: boolean;
  registry_links?: RegistryLink[];
  recipients?: RecipientIn[];
  ship_to_text?: string | null;
  ship_to_user_id?: string | null;
  ship_to_event_id?: string | null;
}

export type WishInput = Partial<
  Pick<
    Wish,
    "kind" | "name" | "url" | "price_cents" | "goal_cents" | "notes" | "qty"
  >
>;

export interface WishlistQuery {
  person_id?: string;
  household_id?: string;
  owner_id?: string;
}

const B = "/api/v1/wishlists";

export const listWishlists = (q: WishlistQuery = {}) =>
  apiGet<Wishlist[]>(
    `${B}?${new URLSearchParams(q as Record<string, string>)}`,
  );
export const getWishlist = (id: string) =>
  apiGet<WishlistDetail>(`${B}/${seg(id)}`);
/** @brief Member for the ship-to picker; available = usable address. */
export interface ShipPerson {
  id: string;
  display_name: string;
  available: boolean;
}

/** @brief Who gifts can ship to. */
export const listShipPeople = () =>
  apiGet<ShipPerson[]>("/api/v1/wishlists/ship-people");

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
export const claimWish = (
  id: string,
  itemId: string,
  body: { qty?: number; amount_cents?: number },
) => apiPut<WishlistDetail>(`${B}/${seg(id)}/items/${seg(itemId)}/claim`, body);
export const releaseWish = (id: string, itemId: string) =>
  apiDelete<WishlistDetail>(`${B}/${seg(id)}/items/${seg(itemId)}/claim`);
