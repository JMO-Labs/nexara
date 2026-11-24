/**
 * @file lib/auth/ssoErrors.ts
 * @brief Maps backend SSO refusal codes (`/login?error=`) to user copy.
 *        Only mapped strings are ever returned; raw params are never echoed
 *        except the provider name as plain text.
 */
const GENERIC = "Sign-in didn't work. Please try again.";

/**
 * @brief Friendly message for an SSO error code.
 * @param code `error` query value
 * @param provider optional provider display name
 * @return message string
 */
export function ssoErrorMessage(
  code: string,
  provider?: string | null,
): string {
  const name = provider?.trim()
    ? provider.trim().slice(0, 60)
    : "sign-in provider";
  switch (code) {
    case "sso_no_account":
      return "Your account isn't set up here yet. Ask an admin for an invite.";
    case "sso_account_disabled":
      return "Your account has been disabled. Contact an admin for help.";
    case "sso_domain_not_allowed":
    case "sso_group_required":
      return `Your ${name} account isn't allowed to sign in here.`;
    case "sso_email_unverified_local":
      return "An account with this email exists but its email isn't confirmed. Sign in with your password and confirm your email first.";
    case "sso_provision_conflict":
      return "We couldn't finish setting up your account. Please try again.";
    default:
      return GENERIC;
  }
}
