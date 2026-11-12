"use client";
/**
 * @file components/auth/OAuthButtons.tsx
 * @brief Lists configured OAuth providers as link buttons that kick off the
 *        provider's login redirect (handled entirely by the backend).
 */
import { useEffect, useState } from "react";
import { Button } from "@/components/ui";
import {
  getAuthConfig,
  oauthLoginUrl,
  type OAuthProvider,
} from "@/lib/api/auth";
import { API_BASE } from "@/lib/auth/session";

/**
 * @brief OAuth provider buttons; renders nothing when none configured.
 * @return provider link list or null
 */
export function OAuthButtons() {
  const [providers, setProviders] = useState<OAuthProvider[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAuthConfig()
      .then((cfg) => {
        if (!cancelled) setProviders(cfg.oauth_providers);
      })
      .catch(() => {
        if (!cancelled) setProviders([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!providers || providers.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-center text-sm opacity-70">or continue with</p>
      {providers.map((p) => (
        <Button key={p.slug} asChild variant="outline" className="w-full">
          <a href={oauthLoginUrl(p.slug, API_BASE)}>{p.display_name}</a>
        </Button>
      ))}
    </div>
  );
}
