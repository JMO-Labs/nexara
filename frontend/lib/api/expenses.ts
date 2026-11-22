/**
 * @file lib/api/expenses.ts
 * @brief Shared expense ledgers REST client (snake_case wire format, cents).
 */
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, seg } from "./client";

export interface LedgerSummary {
  id: string;
  name: string;
  currency: string;
  event_id: string | null;
  wishlist_id: string | null;
  member_count: number;
  archived: boolean;
  created_at: string;
}

export interface LedgerMember {
  user_id: string;
  name: string;
}

export interface ExpenseShare {
  user_id: string;
  name: string;
  amount_cents: number;
}

export interface LedgerExpense {
  id: string;
  payer_id: string;
  payer_name: string;
  amount_cents: number;
  description: string;
  spent_on: string;
  created_at: string;
  shares: ExpenseShare[];
}

export interface Balance {
  user_id: string;
  name: string;
  cents: number;
}

export interface Transfer {
  from_user_id: string;
  from_name: string;
  to_user_id: string;
  to_name: string;
  cents: number;
}

export interface Ledger extends LedgerSummary {
  created_by: string;
  can_manage: boolean;
  members: LedgerMember[];
  balances: Balance[];
  transfers: Transfer[];
  expenses: LedgerExpense[];
}

export interface LedgerInput {
  name: string;
  currency?: string | null;
  event_id?: string | null;
  wishlist_id?: string | null;
  member_ids: string[];
}

export interface ExpenseInput {
  payer_id: string;
  amount_cents: number;
  description: string;
  spent_on: string;
  split: "equal" | "custom";
  split_among?: string[] | null;
  shares?: { user_id: string; amount_cents: number }[] | null;
}

export interface SettleInput {
  from_user_id: string;
  to_user_id: string;
  amount_cents: number;
}

/** @brief ISO 4217 codes offered in settings (mirrors the backend list). */
export const CURRENCIES = (
  "USD EUR GBP CAD AUD NZD CHF SEK NOK DKK JPY CNY INR MXN BRL ZAR SGD HKD KRW PLN CZK HUF " +
  "ILS TRY AED THB PHP IDR MYR CLP COP ARS"
).split(" ");

const BASE = "/api/v1/expenses";
const L = `${BASE}/ledgers`;

/**
 * @brief Format cents as money.
 * @param cents integer minor units
 * @param currency ISO 4217 code
 * @param locale optional BCP 47 locale (browser default when omitted)
 * @return e.g. "$12.50"
 */
export function formatCents(
  cents: number,
  currency: string,
  locale?: string,
): string {
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
    }).format(cents / 100);
  } catch {
    return `${(cents / 100).toFixed(2)} ${currency}`;
  }
}

/** @brief Community default currency. */
export const getCurrency = () =>
  apiGet<{ currency: string }>(`${BASE}/currency`);
/** @brief Admin: set the community default currency. */
export const setCurrency = (currency: string) =>
  apiPut<{ currency: string }>(`${BASE}/currency`, { currency });

/** @brief My ledgers, optionally for one event or wishlist. */
export const listLedgers = (
  p: { event_id?: string; wishlist_id?: string } = {},
) => {
  const qs = new URLSearchParams();
  if (p.event_id) qs.set("event_id", p.event_id);
  if (p.wishlist_id) qs.set("wishlist_id", p.wishlist_id);
  const s = qs.toString();
  return apiGet<LedgerSummary[]>(s ? `${L}?${s}` : L);
};
export const getLedger = (id: string) => apiGet<Ledger>(`${L}/${seg(id)}`);
export const createLedger = (body: LedgerInput) => apiPost<Ledger>(L, body);
export const updateLedger = (
  id: string,
  body: { name?: string; archived?: boolean },
) => apiPatch<Ledger>(`${L}/${seg(id)}`, body);
export const addLedgerMembers = (id: string, user_ids: string[]) =>
  apiPost<Ledger>(`${L}/${seg(id)}/members`, { user_ids });
export const removeLedgerMember = (id: string, userId: string) =>
  apiDelete(`${L}/${seg(id)}/members/${seg(userId)}`);
export const addExpense = (id: string, body: ExpenseInput) =>
  apiPost<Ledger>(`${L}/${seg(id)}/expenses`, body);
export const deleteExpense = (id: string, expenseId: string) =>
  apiDelete<Ledger>(`${L}/${seg(id)}/expenses/${seg(expenseId)}`);
export const settle = (id: string, body: SettleInput) =>
  apiPost<Ledger>(`${L}/${seg(id)}/settle`, body);
/** @brief "Split this gift": reuse or create the ledger for a wishlist item. */
export const splitGift = (itemId: string) =>
  apiPost<Ledger>(`${L}/from-wishlist-item/${seg(itemId)}`);
