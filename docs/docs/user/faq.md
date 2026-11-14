# FAQ

## What is Nexara?
A self-hosted community platform for families, clubs and groups, with
events, sharing and notifications.

## Who owns my data?
You do. Everything is stored in your own PostgreSQL database and storage
backend; nothing is sent to a third party.

## Does Nexara support SSO / OIDC?
Yes. Set `OIDC_ISSUER`, `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET`, or add
providers in the admin panel. See [SSO / OIDC](../developer/sso-oidc.md).

## How do I set up email?
Fill in the `SMTP_*` variables in `.env` and restart. Without them, no
email (invites, password resets) is sent.

## Are push notifications supported?
Yes. Nexara delivers in-app, Web Push and email notifications. Each user
chooses channels per notification type in their settings. Web Push needs
HTTPS.

## How do I back up my instance?
Use `pg_dump` and back up your file storage. See
[Backups](self-hosting.md#backups).

## How do I upgrade?
Pull new images and run `docker compose up -d`. See
[Upgrades](self-hosting.md#upgrades).

## How do I reset a password?
Use "Forgot password" on the login page (requires email to be configured).
Otherwise ask your instance admin for help.

## Can I restrict who signs up?
Yes. Set `ENABLE_REGISTRATION=false` or `REQUIRE_INVITE=true`.

## Where do I report bugs?
Open an issue in the project's GitHub repository, JMO-Labs/nexara.
