/**
 * @file tests/unit/admin/sso/fixtures.ts
 * @brief Shared preset fixtures for the SSO wizard tests.
 */
import type { OAuthPreset } from "@/lib/api/adminOauth";

const base = {
  scopes: "openid email profile",
  help: "",
  params: [] as string[],
  defaults: {} as Record<string, string>,
  authorization_endpoint: null,
  token_endpoint: null,
  userinfo_endpoint: null,
  claim_mapping: {} as Record<string, string>,
  username_claim: "preferred_username",
};

export const PRESETS: OAuthPreset[] = [
  {
    ...base,
    key: "authentik",
    kind: "oidc",
    label: "authentik",
    discovery_url:
      "https://{host}/application/o/{slug}/.well-known/openid-configuration",
    params: ["host", "slug"],
    claim_mapping: { groups: "groups" },
    help: "Create an OAuth2/OIDC provider + application.",
  },
  {
    ...base,
    key: "github",
    kind: "oauth2",
    label: "GitHub",
    discovery_url: null,
    authorization_endpoint: "https://github.com/login/oauth/authorize",
    token_endpoint: "https://github.com/login/oauth/access_token",
    userinfo_endpoint: "https://api.github.com/user",
    scopes: "read:user user:email read:org",
  },
  {
    ...base,
    key: "custom",
    kind: "oidc",
    label: "Custom OIDC",
    discovery_url: "{discovery_url}",
    params: ["discovery_url"],
  },
];

export const GROUPS = [
  { id: "g-smith", name: "Smith Family" },
  { id: "g-club", name: "Book Club" },
];
