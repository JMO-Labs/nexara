/**
 * @file lib/customCss.ts
 * @brief Size helpers for admin custom CSS.
 */

/** @brief Max stored custom CSS size in bytes (mirrors backend MAX_CSS_BYTES). */
export const MAX_CSS_BYTES = 10240;

/**
 * @brief UTF-8 byte length of a string.
 * @param s text
 * @return number of bytes
 */
export const cssByteLength = (s: string): number =>
  new TextEncoder().encode(s).length;
