# Link Previews

Posts and chat messages are scanned for URLs (max 10, code blocks skipped). Each
URL is scraped for OpenGraph metadata by the Celery task `scrape_link_preview`
and cached in `link_previews` (global, keyed by SHA-256 of the URL).

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/link-previews/{preview_id}` | none | Preview by UUID. `Cache-Control` set from remaining TTL. |
| GET | `/api/v1/link-previews/{preview_id}/image` | none | Proxies the preview image; 60 req/min per IP. 404 if none/unavailable. |
| POST | `/api/v1/link-previews/scrape` | admin | Body `{"url": "https://..."}`; enqueues a scrape (202). 10 req/min. |

`LinkPreviewResponse`: `id, url, og_title, og_description, og_image,
og_site_name, provider_type, provider_id, created_at, cache_ttl_seconds`.

Errors use the standard envelope (`NOT_FOUND`, `VALIDATION_ERROR`); a malformed
`preview_id` yields 422.

## SSRF protection

- Hostname is resolved; any private, loopback or reserved address rejects the URL
  (`localhost`, `127.0.0.1`, `::1` rejected without DNS).
- Unresolvable hosts are rejected.
- All outbound requests use a 5 s timeout. Scrape bodies are capped at 1 MB.
- The image proxy does not follow redirects, only serves `image/*` (SVG excluded),
  and caps size at 5 MB.

## Video providers

YouTube, Vimeo, Twitch, PeerTube, Dailymotion. Detected provider and video ID are
stored in `provider_type` / `provider_id`.
