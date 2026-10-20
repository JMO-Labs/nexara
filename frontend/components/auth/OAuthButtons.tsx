"use client";
/**
 * @file components/auth/OAuthButtons.tsx
 * @brief Lists configured OAuth providers as link buttons that kick off the
 *        provider's login redirect (handled entirely by the backend).
 */
import { useEffect, useState } from "react";
import Stack from "@mui/joy/Stack";
import Divider from "@mui/joy/Divider";
import Typography from "@mui/joy/Typography";
import JoyButton from "@mui/joy/Button";
import {
  getAuthConfig,
  oauthLoginUrl,
  type OAuthProvider,
} from "@/lib/api/auth";
import { API_BASE } from "@/lib/auth/session";

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
    <Stack spacing={2}>
      <Divider>
        <Typography level="body-xs" color="neutral">
          or continue with
        </Typography>
      </Divider>
      <Stack spacing={1}>
        {providers.map((p) => (
          <JoyButton
            key={p.slug}
            variant="outlined"
            color="neutral"
            component="a"
            href={oauthLoginUrl(p.slug, API_BASE)}
            fullWidth
          >
            {p.display_name}
          </JoyButton>
        ))}
      </Stack>
    </Stack>
  );
}
