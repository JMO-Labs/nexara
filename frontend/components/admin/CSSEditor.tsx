/**
 * @file components/admin/CSSEditor.tsx
 * @brief Admin custom CSS editor: highlighted code, byte limit, live preview, save.
 */
"use client";

import { useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { useUpdateBranding } from "@/hooks/useBranding";
import { formatApiError } from "@/lib/api/errors";
import { MAX_CSS_BYTES, cssByteLength, tokenizeCss } from "@/lib/cssHighlight";
import { useToasts } from "@/stores/toasts";
import { CSSPreview } from "./CSSPreview";

const TOKEN_CLASS: Record<string, string> = {
  comment: "tok-comment italic text-muted-foreground",
  string: "tok-string text-emerald-700 dark:text-emerald-300",
  atrule: "tok-atrule text-fuchsia-700 dark:text-fuchsia-300",
  selector: "tok-selector text-sky-700 dark:text-sky-300",
  property: "tok-property text-violet-700 dark:text-violet-300",
  value: "tok-value text-amber-800 dark:text-amber-300",
};

const FIELD =
  "m-0 whitespace-pre-wrap break-words p-3 font-mono text-sm leading-6";

/**
 * @brief Highlighted read-only mirror of the textarea contents.
 * @param code CSS text
 */
function Highlight({ code }: { code: string }) {
  const tokens = useMemo(() => tokenizeCss(code), [code]);
  return (
    <>
      {tokens.map((t, i) =>
        TOKEN_CLASS[t.type] ? (
          <span key={i} className={TOKEN_CLASS[t.type]}>
            {t.text}
          </span>
        ) : (
          t.text
        ),
      )}
      {"\n"}
    </>
  );
}

/**
 * @brief Self-contained custom CSS editor with save/reset/copy.
 * @param initial Stored `branding.custom_css`.
 */
export function CSSEditor({ initial }: { initial: string }) {
  const [saved, setSaved] = useState(initial);
  const [css, setCss] = useState(initial);
  const mirror = useRef<HTMLPreElement>(null);
  const update = useUpdateBranding();
  const push = useToasts((s) => s.push);

  const bytes = cssByteLength(css);
  const tooBig = bytes > MAX_CSS_BYTES;
  const dirty = css !== saved;
  const canSave = dirty && !tooBig && !update.isPending;

  const save = () => {
    if (!canSave) return;
    const body = css;
    update.mutate(
      { custom_css: body },
      {
        onSuccess: () => setSaved(body),
        onError: (err) =>
          push({ variant: "danger", message: formatApiError(err) }),
      },
    );
  };

  const copy = () => {
    navigator.clipboard
      .writeText(css)
      .then(() => push({ variant: "success", message: "CSS copied" }))
      .catch(() => push({ variant: "danger", message: "Copy failed" }));
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="flex flex-col gap-2">
        <label htmlFor="custom-css" className="text-sm font-medium">
          Custom CSS
        </label>
        <div className="relative h-72 overflow-hidden rounded-md border bg-surface">
          <pre
            ref={mirror}
            aria-hidden="true"
            data-testid="css-highlight"
            className={`${FIELD} pointer-events-none absolute inset-0 overflow-hidden`}
          >
            <Highlight code={css} />
          </pre>
          <textarea
            id="custom-css"
            aria-describedby="custom-css-warning custom-css-count"
            className={`${FIELD} absolute inset-0 h-full w-full resize-none overflow-auto bg-transparent text-transparent caret-black dark:caret-white outline-none focus-visible:ring-2 focus-visible:ring-accent`}
            value={css}
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            onChange={(e) => setCss(e.target.value)}
            onScroll={(e) => {
              if (mirror.current) {
                mirror.current.scrollTop = e.currentTarget.scrollTop;
                mirror.current.scrollLeft = e.currentTarget.scrollLeft;
              }
            }}
          />
        </div>
        <p
          id="custom-css-count"
          aria-live="polite"
          className={`text-sm ${bytes > MAX_CSS_BYTES * 0.8 ? "font-semibold text-destructive" : "text-muted-foreground"}`}
        >
          {bytes.toLocaleString("en-US")} /{" "}
          {MAX_CSS_BYTES.toLocaleString("en-US")} bytes
        </p>
        <p
          id="custom-css-warning"
          role="note"
          className="text-sm text-muted-foreground"
        >
          CSS can break site layout. Dangerous patterns (XSS) are blocked.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            onClick={save}
            disabled={!canSave}
            loading={update.isPending}
          >
            Save CSS
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => setCss(saved)}
            disabled={!dirty || update.isPending}
          >
            Reset
          </Button>
          <Button type="button" variant="ghost" onClick={copy}>
            Copy
          </Button>
        </div>
      </div>
      <CSSPreview css={css} />
    </div>
  );
}
