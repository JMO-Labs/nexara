"use client";
/**
 * @file lib/lists/fieldTypes/TextField.tsx
 * @brief Text field (input or textarea).
 */
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Checkbox } from "@/components/ui/Checkbox";
import {
  str,
  textView,
  type FieldConfigEditorProps,
  type FieldEditProps,
  type FieldType,
} from "./base";

function Edit({ config, value, onChange, label }: FieldEditProps) {
  const p = {
    "aria-label": label ?? "Text",
    value: str(value),
  };
  return config.multiline === true ? (
    <Textarea {...p} onChange={(e) => onChange(e.target.value)} />
  ) : (
    <Input {...p} onChange={(e) => onChange(e.target.value)} />
  );
}

function ConfigEditor({ config, onChange }: FieldConfigEditorProps) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <Checkbox
        checked={config.multiline === true}
        onCheckedChange={(c) => onChange({ ...config, multiline: c === true })}
      />
      Multi-line text
    </label>
  );
}

/** @brief Text field type. */
export const TextField: FieldType = {
  key: "text",
  label: "Text",
  View: textView((v) => str(v)),
  Edit,
  ConfigEditor,
};
