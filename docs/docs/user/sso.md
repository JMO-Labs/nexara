# Single sign-on (SSO)

Nexara supports OIDC providers (Keycloak, Authentik, Entra ID, Okta, Google).
See [SSO with generic OpenID Connect](../developer/sso-oidc.md) for setup.

## SSO-only mode

Enterprise deployments (for example a small organization that requires
corporate Keycloak login) can disable all non-SSO authentication.

When enabled:

- `POST /api/v1/auth/login`, `POST /api/v1/auth/register`,
  `POST /api/v1/auth/magic-link/request` and `GET /api/v1/auth/magic-link/verify`
  return **403** with `Single sign-on only: password login is disabled`.
- `GET /api/v1/auth/config` reports `local_auth_enabled: false` and
  `sso_only: true`, so the login page shows only SSO provider buttons.
- New members are provisioned just-in-time on their first SSO login.

### Enable / disable (admin)

```http
PATCH /api/v1/admin/settings/sso-only
{"enabled": true}
```

Enabling fails with **422** unless at least one OIDC provider is configured and
enabled. Changes are written to the audit log.

### Security warning: lockout risk

Once enabled, ensure an SSO provider is configured. Users cannot log in
without it. If the sole provider is broken, disabled or removed, **everyone,
including admins, is locked out**. Test SSO login with a second session before
enabling, and do not remove the last provider while SSO-only is on.

### Recovery

From the backend host or container, disable the toggle directly in the database:

```bash
cd backend && uv run python scripts/reset_sso_only.py
```

This sets `sso_only = false` for the default community; password login works
again immediately. Fix the provider, then re-enable the toggle.
