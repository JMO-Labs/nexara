/**
 * @file lib/slug.ts
 * @brief Slug utility — normalize and validate URL-safe identifiers.
 */

/**
 * Convert a string to a slug: lowercase, replace runs of non-alphanumeric
 * characters with dashes, trim leading/trailing dashes, and drop leading
 * symbols to ensure first char is [a-z0-9].
 *
 * @param input The input string to slugify.
 * @return A normalized slug, or empty string if input is empty.
 */
export function slugify(input: string): string {
  if (!input) return "";

  const result = input
    .toLowerCase()
    .replace(/[^\w-]/g, "-") // Replace non-word chars (except dash) with dash
    .replace(/-+/g, "-") // Collapse multiple dashes
    .replace(/^[-_]+/, "") // Remove leading dashes/underscores
    .replace(/-+$/, ""); // Remove trailing dashes

  return result;
}

/**
 * Check if a slug matches the valid format: must start with [a-z0-9],
 * followed by zero or more [a-z0-9_-].
 *
 * @param slug The slug to validate.
 * @return true if valid, false otherwise.
 */
export function isValidSlugFormat(slug: string): boolean {
  return /^[a-z0-9][a-z0-9_-]*$/.test(slug);
}
