"use client";
/**
 * @file components/lists/TemplatePreview.tsx
 * @brief Live preview of template fields via registry Edit components.
 */
import { fieldRegistry } from "@/lib/lists/fieldRegistry";
import type { TemplateField } from "@/lib/lists/templateModel";

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
          </div>
        );
      })}
    </div>
  );
}
