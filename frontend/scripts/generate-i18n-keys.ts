/**
 * @file scripts/generate-i18n-keys.ts
 * @brief Generates the TranslationKey union type from the locale JSON.
 *
 * Reads i18n/locales/en-US.json, extracts all dot-separated leaf paths,
 * and writes them as a TypeScript union type to types/i18n-keys.ts.
 *
 * Usage: npx tsx scripts/generate-i18n-keys.ts
 */

import { readFileSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const LOCALE_PATH = resolve(__dirname, "../i18n/locales/en-US.json");
const OUTPUT_PATH = resolve(__dirname, "../types/i18n-keys.ts");

/**
 * @brief Recursively collect dot-separated leaf paths from a nested object.
 * @param obj - The JSON object to traverse.
 * @param prefix - Current path prefix for recursion.
 * @returns Array of dot-separated key paths.
 */
function collectKeys(obj: Record<string, unknown>, prefix = ""): string[] {
  const keys: string[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      keys.push(...collectKeys(value as Record<string, unknown>, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

const locale = JSON.parse(readFileSync(LOCALE_PATH, "utf-8"));
const keys = collectKeys(locale);

const union = keys.map((k) => `  | "${k}"`).join("\n");

const output = `/**
 * @file types/i18n-keys.ts
 * @brief Auto-generated union type of all valid i18n translation keys.
 *
 * Regenerate with: npx tsx scripts/generate-i18n-keys.ts
 * Source: i18n/locales/en-US.json
 */

/** @brief All valid dot-separated translation key paths from the locale file. */
export type TranslationKey =
${union};
`;

writeFileSync(OUTPUT_PATH, output, "utf-8");
console.log(`Generated ${keys.length} translation keys -> ${OUTPUT_PATH}`);
