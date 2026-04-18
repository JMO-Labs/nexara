/**
 * @file utils/email.ts
 * @brief Email validation for self-hosted environments.
 *
 * Accepts non-standard TLDs (.local, .lan, .internal, .home, etc.)
 * that are common in self-hosted / homelab setups.
 */

/**
 * @brief Validate an email address with specific error feedback.
 * @param email The email string to validate.
 * @returns null if valid, or an i18n error key string if invalid.
 */
export function validateEmail(email: string): string | null {
  const trimmed = email.trim();

  if (!trimmed) {
    return "auth.errors.emailRequired";
  }

  if (!trimmed.includes("@")) {
    return "auth.errors.emailMissingAt";
  }

  const atCount = trimmed.split("@").length - 1;
  if (atCount > 1) {
    return "auth.errors.emailMultipleAt";
  }

  const [local, domain] = trimmed.split("@");

  if (!local) {
    return "auth.errors.emailMissingLocal";
  }

  if (!domain) {
    return "auth.errors.emailMissingDomain";
  }

  if (domain.startsWith(".") || domain.endsWith(".")) {
    return "auth.errors.emailInvalidDomain";
  }

  // Allow any TLD including .local, .lan, .home, .internal, etc.
  // Just require at least one character after the last dot (or no dot for bare hostnames)
  const domainParts = domain.split(".");
  if (domainParts.some((part) => part.length === 0)) {
    return "auth.errors.emailInvalidDomain";
  }

  return null;
}
