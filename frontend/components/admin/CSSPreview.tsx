/**
 * @file components/admin/CSSPreview.tsx
 * @brief Sandboxed iframe rendering sample UI with admin custom CSS applied.
 */
"use client";

const SAMPLE = `<main>
<h1>Welcome to the community</h1>
<h2>Upcoming events</h2>
<p>This is sample body text with a <a href="#">link</a>.</p>
<div class="card"><h3>Card title</h3><p>Card body text.</p>
<button type="button" class="btn btn-primary">Primary</button>
<button type="button" class="btn">Secondary</button></div>
</main>`;

// Neutral system colours (no hex): the preview frame is not themed by app tokens.
const BASE_CSS =
  "body{font-family:system-ui,sans-serif;margin:16px;color:CanvasText;background:Canvas}" +
  ".card{border:1px solid color-mix(in srgb,CanvasText 15%,transparent);border-radius:12px;padding:12px;margin-top:12px}" +
  ".btn{padding:6px 12px;border-radius:8px;border:1px solid color-mix(in srgb,CanvasText 25%,transparent);margin-right:8px}" +
  ".btn-primary{background:CanvasText;color:Canvas;border-color:CanvasText}";

/** @brief CSP so admin CSS (`@import`, `url()`) cannot make network requests. */
const PREVIEW_CSP =
  "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:";

/**
 * @brief Build the iframe document; escapes `</style` so CSS cannot inject HTML.
 * @param css admin CSS
 * @return full HTML document string
 */
export function buildPreviewDoc(css: string): string {
  const safe = css.replace(/<\/(style)/gi, "<\\/$1");
  return `<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="${PREVIEW_CSP}"><style>${BASE_CSS}</style><style>${safe}</style></head><body>${SAMPLE}</body></html>`;
}

/**
 * @brief Live preview panel; `sandbox=""` blocks scripts and keeps CSS isolated.
 * @param css current editor CSS
 */
export function CSSPreview({ css }: { css: string }) {
  return (
    <div className="flex min-h-64 flex-col gap-2">
      <span className="text-sm font-medium" id="css-preview-label">
        Live Preview
      </span>
      <iframe
        title="Live Preview"
        aria-labelledby="css-preview-label"
        sandbox=""
        srcDoc={buildPreviewDoc(css)}
        className="glass-item min-h-64 w-full flex-1 rounded-[22px]"
      />
    </div>
  );
}
