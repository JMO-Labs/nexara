/**
 * @file lib/money.ts
 * @brief Money in integer cents: locale formatting and lenient parsing.
 */

/** @brief Currencies offered in pickers (any ISO code works server-side). */
export const CURRENCIES = [
  "USD",
  "CAD",
  "EUR",
  "GBP",
  "AUD",
  "MXN",
  "JPY",
] as const;

/**
 * @brief Format cents for display, e.g. 1250 -> "$12.50".
 * @param cents amount in minor units
 * @param currency ISO 4217 code
 * @return localized string
 */
export function formatMoney(cents: number, currency = "USD"): string {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: cents % 100 === 0 ? 0 : 2,
    }).format(cents / 100);
  } catch {
    return `${(cents / 100).toFixed(2)} ${currency}`;
  }
}

/**
 * @brief Parse user input like "$1,250.5" or "25" into cents.
 * @param text input
 * @return cents, or null when empty/invalid
 */
export function parseMoney(text: string): number | null {
  const clean = text.replace(/[^\d.]/g, "");
  if (!clean) return null;
  const n = Number(clean);
  return Number.isFinite(n) ? Math.round(n * 100) : null;
}

/** @brief Cents to an input value ("12.5" -> "12.50"; whole amounts stay whole). */
export const centsToInput = (c: number | null | undefined) =>
  c == null ? "" : c % 100 === 0 ? String(c / 100) : (c / 100).toFixed(2);
