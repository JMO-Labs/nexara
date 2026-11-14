"use client";
/**
 * @file components/lists/FieldConfigPanel.tsx
 * @brief Type-specific config editor for the selected field.
 */
import { Input } from "@/components/ui/Input";
import { fieldRegistry } from "@/lib/lists/fieldRegistry";
import type { TemplateField } from "@/lib/lists/templateModel";

interface Props {
  field: TemplateField;
  onChange: (patch: Partial<TemplateField>) => void;
}

/**
 * @brief Label input plus the registry ConfigEditor.
 * @param props field and change handler
 * @return panel
 */
export function FieldConfigPanel({ field, onChange }: Props) {
  const Editor = fieldRegistry.get(field.type_key)?.ConfigEditor;
  return (
    <section aria-label="Field settings" className="flex flex-col gap-3">
      <Input
        label="Label"
        value={field.label}
        onChange={(e) => onChange({ label: e.target.value })}
      />
      {Editor && (
        <Editor
          config={field.config}
          onChange={(config) => onChange({ config })}
        />
      )}
    </section>
  );
}
