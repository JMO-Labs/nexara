# Branding Guide

Admins customize how their community looks under **Admin > Branding**. Changes
are saved per community and take effect for all members. Only admins can edit
branding; the public values are readable without login so the login page,
emails, and PWA manifest can use them.

## Fields

| Field | Applies to | Notes |
| ----- | ---------- | ----- |
| Community name | App header, emails, PWA manifest `name` | 1-100 characters. `short_name` is the first 12 characters. |
| Tagline | App landing and header | Up to 300 characters. |
| Primary | App theme (light mode), emails, PWA `theme_color` | `#RRGGBB` hex. |
| Primary (dark) | App theme (dark mode) | `#RRGGBB` hex. |
| Accent color | App theme (buttons and highlights) | Must reach 4.5:1 contrast against the dark green text used on it. Rejected otherwise. |
| Surface (light) | App theme (light backgrounds), PWA `background_color` | `#RRGGBB` hex. |
| Surface (dark) | App theme (dark backgrounds) | `#RRGGBB` hex. |
| Text (light) | App theme (text on light surfaces) | `#RRGGBB` hex. |
| Text (dark) | App theme (text on dark surfaces) | `#RRGGBB` hex. |
| Font family | App theme (body text) | Pick from the list: Inter, Roboto, Open Sans, Lato, Poppins, Montserrat, Source Sans 3, Noto Sans, Raleway, Ubuntu, system-ui. |
| Monospace font | App theme (code) | JetBrains Mono, Fira Code, Source Code Pro, IBM Plex Mono. |
| Logo (light / dark) | App header | Uploaded media. Emails use it when no email logo is set. |
| Email logo | Emails | Overrides the light logo in emails. |
| Email footer text | Emails | Shown in the footer of every email. |
| Email sender name | Emails (From header) | See [Sender name](#email-sender-name). |
| Landing call to action | Public landing page | Default: "Join our community". |
| Show feature list | Public landing page | On by default. |
| About (short) | Public landing page | Short description of the community. |
| PWA icon 192 / 512 | PWA manifest | PNG media, 192x192 and 512x512. Without them the manifest falls back to `/favicon.ico`. |
| Custom CSS | App theme | Off until enabled. See [Custom CSS](admin-custom-css.md). |

## Where it takes effect

- **App theme**: colors, fonts, logos, and name apply to the whole web app,
  in light and dark mode. The preview in the editor shows the result before
  you save.
- **Emails**: community name, primary color, logo, footer text, and sender
  name.
- **PWA manifest**: served at `/api/v1/branding/manifest.json`. Contains name,
  `theme_color`, `background_color`, and icons. Members who already installed
  the app may need to reinstall it to see new icons.

## Contrast warnings (WCAG)

Nexara checks two pairs against WCAG 2.1 AA (4.5:1 for normal text):

- Text (light) on Surface (light)
- Text (dark) on Surface (dark)

If a pair falls below 4.5:1 the editor shows a warning such as
"Text (light): 3.10:1 is below 4.5:1 (warning only)". The API also returns
these in `contrast_warnings` after saving. **Warnings do not block saving**;
you decide whether to keep the colors. Aim for 7:1 (AAA) where you can.

The accent color is stricter: it is a hard error, not a warning, when its
contrast with the dark green text is under 4.5:1.

Only colors you change are validated, so older saved values never block an
unrelated edit.

## Email sender name

The sender name changes **only the display name** in the From header
(for example `Smith Family <noreply@example.com>`). The address still comes
from the `SMTP_FROM` environment variable and cannot be changed from the
admin panel. Leave the field empty to send with the bare address.

## Tips

- Check both light and dark mode in the preview.
- Use square PNG icons with some padding so they survive masking on phones.
