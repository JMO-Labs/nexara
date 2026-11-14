"use client";
/**
 * @file lib/lists/fieldTypes/CheckboxField.tsx
 * @brief Checkbox field with completion_mode config.
 */
import { Checkbox } from "@/components/ui/Checkbox";
import type {
  FieldConfigEditorProps,
  FieldEditProps,
  FieldType,
  FieldViewProps,
} from "./base";

function View({ value }: FieldViewProps) {
  return <span>{value ? "Done" : "Not done"}</span>;
}

function Edit({ value, onChange, label }: FieldEditProps) {
  return (
    <Checkbox
      aria-label={label ?? "Done"}
      checked={value === true}
      onCheckedChange={(c) => onChange(c === true)}
    />
  );
}

function ConfigEditor({ config, onChange }: FieldConfigEditorProps) {
  return (
    <label className="flex flex-col gap-1.5 text-sm font-semibold">
      Completion mode
      <select
        className="h-10 rounded-md border border-input bg-transparent px-2 font-normal"
        value={config.completion_mode === "all" ? "all" : "any"}
        onChange={(e) =>
          onChange({ ...config, completion_mode: e.target.value })
        }
      >
        <option value="any">Any member can complete</option>
        <option value="all">All members must complete</option>
      </select>
    </label>
  );
}

/** @brief Checkbox field type. */
export const CheckboxField: FieldType = {
  key: "checkbox",
  label: "Checkbox",
  View,
  Edit,
  ConfigEditor,
};
