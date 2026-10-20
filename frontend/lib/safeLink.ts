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
    if (u.origin !== "http://x.invalid") return null;
    const out = u.pathname + u.search + u.hash;
    // normalization can turn "/.//evil.com" into protocol-relative "//evil.com"
    return out[1] === "/" || out[1] === "\\" ? null : out;
  } catch {
    return null;
  }
}
