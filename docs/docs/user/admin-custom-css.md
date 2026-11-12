# Custom CSS (admin)

Admins can add custom CSS under Admin > Branding. Enable the toggle and paste CSS (max 10 KB).

## Allowed

Colors, fonts, layout (flexbox, grid, margin, padding, sizes), transforms,
transitions, animations, `@keyframes`, `@media`, pseudo-classes (`:hover`)
and pseudo-elements (`::before`).

```css
.btn:hover { background: #3b82f6; transform: translateY(-1px); }
@media (max-width: 600px) { h1 { font-size: 1.25rem; } }
```

## Blocked (removed server-side)

- `@import` rules
- `url()` using `javascript:`, `data:` or `vbscript:`
- `expression(...)`
- `behavior:` properties
- `vbscript:` / `jscript:` protocols
- `<style` tags and CSS comments

## Security model

CSS is sanitized on save by a deny-list that is re-applied until stable, so nested
payloads cannot reassemble. The stored (sanitized) version is what is served.
Saving fails with HTTP 400 when:

- `css_too_large`: over 10 KB.
- `css_invalid`: more than half of the input had to be removed.

CSS can still break your layout; test changes before enabling.
