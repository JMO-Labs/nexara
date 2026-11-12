"use client";
/**
 * @file components/auth/OAuthButtons.tsx
 * @brief Lists configured OAuth providers as link buttons that kick off the
 *        provider's login redirect (handled entirely by the backend).
 */
import { Button } from "@/components/ui";
import { oauthLoginUrl, type OAuthProvider } from "@/lib/api/auth";
import { API_BASE } from "@/lib/auth/session";

/**
 * @brief OAuth provider buttons; renders nothing when none configured.
 * @param providers enabled providers
 * @param showDivider render separator above the section
 * @return provider link list or null
 */
export function OAuthButtons({
  providers,
  showDivider = true,
}: {
  providers: OAuthProvider[];
  showDivider?: boolean;
}) {
  if (providers.length === 0) return null;

  return (
    <section aria-labelledby="sso-heading" className="flex flex-col gap-3">
      {showDivider && (
        <div role="separator" className="border-t border-current/20" />
      )}
      <h2 id="sso-heading" className="text-center text-sm opacity-70">
        Sign in with SSO
      </h2>
      {providers.map((p) => (
        <Button key={p.slug} asChild variant="outline" className="w-full">
          <a href={oauthLoginUrl(p.slug, API_BASE)}>
            {p.icon_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={p.icon_url} alt="" className="size-5" />
            )}
            {p.display_name}
          </a>
        </Button>
      ))}
    </section>
  );
}
