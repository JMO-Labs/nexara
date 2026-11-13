# Installing Nexara on unRAID

This guide installs Nexara from the three templates in `deploy/unraid/`.

## Before you start

- unRAID 6.10 or newer with Docker enabled.
- Create a custom Docker network so containers can find each other by name
  (Terminal: `docker network create nexara-net`).

## Steps

1. **Add the templates.** In the *Docker* tab choose *Add Container*, then
   pick `nexara-postgres` from the *Template* list (copy the XML files from
   `deploy/unraid/` to `/boot/config/plugins/dockerMan/templates-user/`).
2. **Install the database.** Set a *Database Password*, set *Network Type*
   to `nexara-net`, and click *Apply*.
3. **Install Nexara.** Add the `nexara` template and set:
    - *Secret Key*: a long random string (`openssl rand -hex 32`).
    - *Database URL*: `postgresql+asyncpg://nexara:<password>@nexara-postgres:5432/nexara`
      (URL-encode special characters in the password).
    - *WebUI Port*: leave at `8080` unless it is taken.
    - *Network Type*: `nexara-net`.
4. **Optional: separate Valkey.** Nexara bundles Valkey, so this is not
   required. To use the `nexara-valkey` template, install it on `nexara-net`
   and set *Redis/Valkey URL* to `redis://nexara-valkey:6379`.

## Open Nexara

Click the Nexara icon in the Docker tab and choose *WebUI*, or browse to
`http://<unraid-ip>:8080/`.

New accounts get the *member* role. To get an administrator, connect an
OpenID Connect identity provider (`OIDC_*` variables): users in the group
named by `OIDC_ADMIN_GROUP` (default `nexara-admin`) receive the admin role
when they sign in. See the [FAQ](../user/faq.md) and
[self-hosting variables](../user/self-hosting.md).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Page does not load | Check the container log; confirm the port is not used by another container. |
| `could not translate host name "nexara-postgres"` | Both containers must be on the same custom network (not the default `bridge`). |
| Password authentication failed | The password in *Database URL* must match the database template. Changing it later requires removing the postgres data folder. |
| Uploads disappear after update | Make sure *Media Storage* maps to a folder under `/mnt/user/appdata`. |

## See also

- [Deployment guide](deployment-guide.md) for the platform comparison.
- [Security](security.md): put a TLS reverse proxy in front of the WebUI port.
- [Troubleshooting](troubleshooting.md) for database, upload and Celery issues.
