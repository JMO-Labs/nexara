# Branding (admin guide)

Admins customise how the community looks under **Admin > Branding**.
Changes are saved with one button, written to the audit log, and visible to
everyone within about 5 minutes (branding is cached).

## Fields

### Identity

| Field | Affects |
| ----- | ------- |
| Community name (1-100 chars) | App header, emails, PWA manifest `name` (`short_name` is the first 12 characters) |
| Tagline (max 300 chars) | Landing page and app header |

### Palette

All colours are 6-digit hex (`#RRGGBB`).

| Field | Default | Affects |
| ----- | ------- | ------- |
| Primary | `#2f6b45` | Light theme brand colour and buttons; emails; PWA `theme_color` |
| Primary (dark) | `#7bc28f` | Dark theme brand colour |
| Accent | `#C6B4F5` | Highlights in the app theme |
| Surface (light) / (dark) | `#ffffff` / `#1f2937` | Page background per theme; PWA `background_color` uses the light surface |
| Text (light) / (dark) | `#111827` / `#f9fafb` | Body text per theme |

### Fonts

| Field | Default | Choices |
| ----- | ------- | ------- |
| Sans font | Inter | Inter, Roboto, Open Sans, Lato, Poppins, Nunito, system-ui, Arial, Georgia |
| Monospace font | JetBrains Mono | JetBrains Mono, Fira Code, Source Code Pro, IBM Plex Mono, ui-monospace, Courier New |

Fonts apply to the app theme only, not to emails.

### Email branding

| Field | Affects |
| ----- | ------- |
| Email logo | Header of notification emails (falls back to the light logo) |
| Email footer text | Footer of notification emails |
| Email sender name | Display name in the `From` header |
| Primary colour | Accent colour in emails (see above) |

!!! note
    The email sender name changes **only the display name** (for example
    `Our Family <noreply@example.com>`). The address still comes from the
    `SMTP_FROM` setting and cannot be changed here.

### Images and PWA icons

| Field | Affects |
| ----- | ------- |
| Light / dark logo | App header per theme |
| Favicon | Browser tab |
| PWA icon 192x192 and 512x512 (PNG) | Home-screen icon in the PWA manifest (`/api/v1/branding/manifest.json`). Without them the manifest falls back to `/favicon.ico` |
| Social (OG) image | Link previews |
| Landing hero background, call-to-action text, feature-list toggle | Public landing page |

Installed PWAs may need to be reinstalled before browsers pick up a new icon.

## Contrast warnings (WCAG 2.1 AA)

The editor checks these pairs live and shows a warning for each failing one:

| Pair | Minimum ratio |
| ---- | ------------- |
| Text on light surface | 4.5:1 |
| Text on dark surface | 4.5:1 |
| Primary on light surface (large text) | 3:1 |
| Primary (dark) on dark surface (large text) | 3:1 |

Warnings are advisory: you can still save. The server returns the same
`contrast_warnings` list in its save response.

The **accent colour is stricter**. It must reach 4.5:1 against the dark green
text (`#14301E`) placed on it. Lower values are rejected with an error and
cannot be saved. If a stored accent ever fails this check, the app ignores it
and uses the default accent.

## Related

- [Custom CSS](admin-custom-css.md)
