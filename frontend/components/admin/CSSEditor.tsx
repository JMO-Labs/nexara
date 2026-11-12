/**
 * @file components/admin/CSSEditor.tsx
 * @brief Admin custom CSS editor: CodeMirror 6, byte limit, live preview, save.
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { css as cssLang } from "@codemirror/lang-css";
import { syntaxHighlighting } from "@codemirror/language";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap, lineNumbers } from "@codemirror/view";
import { classHighlighter } from "@lezer/highlight";
import { Button } from "@/components/ui";
import { useUpdateBranding } from "@/hooks/useBranding";
import { MAX_CSS_BYTES, cssByteLength } from "@/lib/customCss";
import { useToasts } from "@/stores/toasts";
import { CSSPreview } from "./CSSPreview";

/** @brief Theme-aware colours for the stable `tok-*` classes from classHighlighter. */
const TOKEN_STYLES =
  "[&_.tok-comment]:italic [&_.tok-comment]:text-muted-foreground " +
  "[&_.tok-string]:text-emerald-700 dark:[&_.tok-string]:text-emerald-300 " +
  "[&_.tok-keyword]:text-fuchsia-700 dark:[&_.tok-keyword]:text-fuchsia-300 " +
  "[&_.tok-typeName]:text-sky-700 dark:[&_.tok-typeName]:text-sky-300 " +
  "[&_.tok-className]:text-sky-700 dark:[&_.tok-className]:text-sky-300 " +
  "[&_.tok-propertyName]:text-violet-700 dark:[&_.tok-propertyName]:text-violet-300 " +
  "[&_.tok-number]:text-amber-800 dark:[&_.tok-number]:text-amber-300 " +
  "[&_.tok-atom]:text-amber-800 dark:[&_.tok-atom]:text-amber-300";

const EDITOR_THEME = EditorView.theme({
  "&": { height: "100%", fontSize: "0.875rem" },
  ".cm-scroller": {
    fontFamily: "var(--font-mono, monospace)",
    lineHeight: "1.5rem",
  },
  "&.cm-focused": { outline: "none" },
});

/**
 * @brief Self-contained custom CSS editor with save/reset/copy.
 * @param initial Stored `branding.custom_css`.
 */
export function CSSEditor({ initial }: { initial: string }) {
  const [saved, setSaved] = useState(initial);
  const [css, setCss] = useState(initial);
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const update = useUpdateBranding("Custom CSS saved");
  const push = useToasts((s) => s.push);

  // Create the EditorView once; later value changes are dispatched into it.
  useEffect(() => {
    if (!host.current) return;
    const v = new EditorView({
      parent: host.current,
      state: EditorState.create({
        doc: initial,
        extensions: [
          lineNumbers(),
          history(),
          keymap.of([...defaultKeymap, ...historyKeymap]),
          cssLang(),
          syntaxHighlighting(classHighlighter),
          EditorView.lineWrapping,
          EDITOR_THEME,
          EditorView.contentAttributes.of({
            "aria-label": "Custom CSS",
            "aria-multiline": "true",
            "aria-describedby": "custom-css-warning custom-css-count",
            spellcheck: "false",
            autocapitalize: "off",
            autocorrect: "off",
          }),
          EditorView.updateListener.of((u) => {
            if (u.docChanged) setCss(u.state.doc.toString());
          }),
        ],
      }),
    });
    view.current = v;
    return () => {
      v.destroy();
      view.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount once
  }, []);

  /** @brief Replace the editor document (reset). */
  const setDoc = (next: string) => {
    const v = view.current;
    if (!v) return setCss(next);
    v.dispatch({ changes: { from: 0, to: v.state.doc.length, insert: next } });
  };

  const bytes = cssByteLength(css);
  const tooBig = bytes > MAX_CSS_BYTES;
  const dirty = css !== saved;
  const canSave = dirty && !tooBig && !update.isPending;

  const save = () => {
    if (!canSave) return;
    const body = css;
    // Error toast is emitted by useUpdateBranding (useMutationWithToast).
    update.mutate({ custom_css: body }, { onSuccess: () => setSaved(body) });
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
        <span aria-hidden="true" className="text-sm font-medium">
          Custom CSS
        </span>
        <div
          ref={host}
          data-testid="css-editor"
          className={`h-72 overflow-hidden rounded-md border bg-surface focus-within:ring-2 focus-within:ring-accent ${TOKEN_STYLES}`}
        />
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
            onClick={() => setDoc(saved)}
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
