"use client";
/**
 * @file lib/lists/fieldTypes/DateField.tsx
 * @brief Date field with is_due_field toggle.
 */
import { Input } from "@/components/ui/Input";
import { Checkbox } from "@/components/ui/Checkbox";
import {
  str,
  textView,
  type FieldConfigEditorProps,
  type FieldEditProps,
  type FieldType,
} from "./base";

function Edit({ value, onChange, label }: FieldEditProps) {
  return (
    <Input
      type="date"
      aria-label={label ?? "Date"}
      value={str(value)}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function ConfigEditor({ config, onChange }: FieldConfigEditorProps) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <Checkbox
        aria-label="Is due date field?"
        checked={config.is_due_field === true}
        onCheckedChange={(c) =>
          onChange({ ...config, is_due_field: c === true })
        }
      />
      Is due date field?
    </label>
  );
}

/** @brief Date field type. */
export const DateField: FieldType = {
  key: "date",
  label: "Date",
  View: textView((v) => str(v)),
  Edit,
  ConfigEditor,
};
