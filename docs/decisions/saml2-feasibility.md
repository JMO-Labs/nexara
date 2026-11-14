# Decision: SAML 2.0 support feasibility

- Status: Accepted (defer to phase 3+)
- Ticket: nexara#203, based on findings in nexara#5

## Context

Nexara ships generic OIDC login (`backend/app/models/oauth_provider.py`,
`services/oauth/`). Some enterprises only expose SAML 2.0 IdPs (on-prem ADFS,
legacy Okta/Ping). We must decide whether to add SAML now, later, or never.

## Library evaluation

The backend is FastAPI, so `djangosaml2` (a Django-only wrapper around
pysaml2) is not applicable.

| Library | Maturity | License | Ease of use | Cost |
|---|---|---|---|---|
| python3-saml (OneLogin) | Mature, widely deployed, active | MIT | High: framework-agnostic, small API (`OneLogin_Saml2_Auth`) | Needs `lxml` + `xmlsec` native libs in images |
| pysaml2 | Mature, full-featured (IdP and SP) | Apache-2.0 | Low-medium: large API, verbose config | Needs `xmlsec1` binary; heavier maintenance |
| signxml | Mature, focused | Apache-2.0 | Low: only XML signature verify; the whole SAML flow is DIY | Least native baggage, most own code and security risk |
| djangosaml2 | Mature | Apache-2.0 | N/A: Django only | Not usable |

Best fit if we build it: **python3-saml**.

## Effort estimate (basic SP-initiated SSO)

~8-12 dev days: SP metadata endpoint, ACS endpoint, IdP metadata import,
signature and assertion validation, reuse of claim/group mapping and user
provisioning, migration relaxing OIDC-only NOT NULL columns
(`client_id`, `client_secret_encrypted`), admin UI, tests against Keycloak
in SAML mode. Add 3-5 days for SLO, certificate rotation and IdP-initiated
flow.

## OIDC vs SAML for self-hosted deployments

| Aspect | OIDC | SAML 2.0 |
|---|---|---|
| Format | JSON/JWT | XML + XML-DSig |
| Config | Discovery URL, client id/secret | Metadata exchange, certificates |
| Security surface | Small (PKCE, JWT checks) | Large (XSW, XXE, replay, InResponseTo) |
| Dependencies | Pure Python | Native `xmlsec`; complicates Docker/Helm images and Trivy scans |
| Cert management | JWKS auto-rotation | Manual or metadata-driven rotation |
| Admin effort | Low | Higher; error-prone for small clubs and families |
| Coverage | Keycloak, Authentik, Google Workspace, Entra, modern Okta | Everything above plus legacy on-prem ADFS, Ping, old Okta |

## Use cases

SAML is needed by: large enterprises and universities with ADFS or Shibboleth
(InCommon/eduGAIN federations), government and regulated sectors with
SAML-only mandates, and legacy Okta/Ping tenants. Nexara's target (families,
clubs, small groups) is served by OIDC and local accounts.

## Recommendation

**Defer to phase 3+.** OIDC covers the target audience and most enterprise
IdPs. SAML adds roughly 2 weeks of work, a security-sensitive XML surface,
a native dependency in every image, and ongoing maintenance, without a
concrete customer. Revisit when a real SAML-only requirement appears.

### Future CORE ticket scope

1. Add `python3-saml` and `xmlsec` to images; update Helm and Trivy config.
2. Migration: allow `provider_type="saml"`, make `client_id` and
   `client_secret_encrypted` nullable, add SAML columns (IdP entity id, SSO
   URL, x509 cert, SP cert/key).
3. Endpoints: SP metadata, ACS, SP-initiated login.
4. Reuse `claim_mapper`, `group_mapper`, `user_provisioner`.
5. Hardening: signed assertions required, XXE disabled, InResponseTo and
   replay cache (Valkey), clock-skew limits.
6. Admin UI for IdP metadata import; docs; Keycloak SAML integration tests.
7. Follow-up: SLO, cert rotation, IdP-initiated login.
