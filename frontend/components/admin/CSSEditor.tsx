/**
 * @file components/admin/CSSEditor.tsx
 * @brief Textarea for admin custom CSS with a security warning.
 */
"use client";

interface CSSEditorProps {
  value: string;
  onChange: (value: string) => void;
}

/**
 * @brief Custom CSS editor.
 * @param value Current CSS text.
 * @param onChange Called with the new text.
 */
export function CSSEditor({ value, onChange }: CSSEditorProps) {
  return (
    <div className="space-y-2">
      <label htmlFor="custom-css" className="text-sm font-medium">
        Custom CSS
      </label>
      <textarea
        id="custom-css"
        aria-describedby="custom-css-warning"
        className="min-h-48 w-full rounded-md border p-2 font-mono text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
      />
      <p id="custom-css-warning" role="note" className="text-sm text-muted-foreground">
        CSS can break site layout. Use carefully. XSS-dangerous patterns are
        blocked server-side.
      </p>
    </div>
  );
}
