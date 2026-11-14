"use client";
/**
 * @file components/lists/TemplatePreview.tsx
 * @brief Live preview of template fields via registry Edit components.
 */
import { fieldRegistry } from "@/lib/lists/fieldRegistry";
import { optionsOf } from "@/lib/lists/fieldTypes/base";
import type { TemplateField } from "@/lib/lists/templateModel";

/**
 * @brief List configured option labels (closed selects hide them).
 * @param props field
 * @return option chips or null
 */
function OptionHints({ field }: { field: TemplateField }) {
  const opts = optionsOf(field.config).filter((o) => o.label || o.value);
  if (opts.length === 0) return null;
  return (
    <ul
      aria-label={`${field.label} options`}
      className="flex flex-wrap gap-1 text-xs text-muted-foreground"
    >
      {opts.map((o, i) => (
        <li key={`${o.value}-${i}`} className="rounded border px-1.5 py-0.5">
          {o.label || o.value}
        </li>
      ))}
    </ul>
  );
}

/**
 * @brief Render each field as an (inert) form row.
 * @param props fields
 * @return preview
 */
export function TemplatePreview({ fields }: { fields: TemplateField[] }) {
  return (
    <div data-testid="template-preview" className="flex flex-col gap-3">
      {fields.map((f) => {
        const Edit = fieldRegistry.get(f.type_key)?.Edit;
        return (
          <div key={f.id} className="flex flex-col gap-1">
            <span className="text-sm font-medium">{f.label}</span>
            {Edit && (
              <Edit
                config={f.config}
                value={undefined}
                onChange={() => {}}
                label={f.label}
              />
            )}
            <OptionHints field={f} />
          </div>
        );
      })}
    </div>
  );
}
