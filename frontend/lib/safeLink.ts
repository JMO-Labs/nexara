/**
 * @file lib/safeLink.ts
 * @brief Accept only same-origin relative paths for server/user-supplied links.
 */

/**
 * @brief Validate an untrusted link value.
 * @param v untrusted value (e.g. notification payload.link)
 * @return the path if it is a same-origin relative path, else null
 */
export function safeInternalLink(v: unknown): string | null {
  if (typeof v !== "string" || !v.startsWith("/")) return null;
  if (v.startsWith("//") || v.startsWith("/\\")) return null;
  try {
    const u = new URL(v, "http://x.invalid");
    return u.origin === "http://x.invalid"
      ? u.pathname + u.search + u.hash
      : null;
  } catch {
    return null;
  }
}
