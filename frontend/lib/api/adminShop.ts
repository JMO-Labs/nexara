/**
 * @file lib/api/adminShop.ts
 * @brief Admin Amazon Creators API settings (wishlist live prices).
 */
import { apiGet, apiPost, apiPut } from "./client";

export interface AmazonSettings {
  client_id: string;
  partner_tag: string;
  marketplace: string;
  has_secret: boolean;
  /** Where the keys in use come from; null when Amazon is off. */
  source: "admin" | "server" | null;
}

export type AmazonUpdate = Partial<{
  client_id: string;
  client_secret: string;
  partner_tag: string;
  marketplace: string;
}>;

const URL = "/api/v1/admin/shop/amazon";

/** @brief Saved settings (the secret is never returned). */
export const getAmazon = () => apiGet<AmazonSettings>(URL);
/** @brief Save settings; '' clears a field. */
export const putAmazon = (body: AmazonUpdate) =>
  apiPut<AmazonSettings>(URL, body);
/** @brief Try the keys against Amazon. */
export const testAmazon = () =>
  apiPost<{ success: boolean; message: string }>(`${URL}/test`);
