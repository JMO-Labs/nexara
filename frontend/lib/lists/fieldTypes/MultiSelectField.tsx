"use client";
/**
 * @file lib/lists/fieldTypes/MultiSelectField.tsx
 * @brief Multi-select field (checkbox group).
 */
import { Checkbox } from "@/components/ui/Checkbox";
import {
  optionsOf,
  type FieldEditProps,
  type FieldType,
  type FieldViewProps,
} from "./base";
import { OptionsEditor } from "./OptionsEditor";

const arr = (v: unknown): string[] => (Array.isArray(v) ? (v as string[]) : []);

function View({ config, value }: FieldViewProps) {
  const sel = arr(value);
  if (!sel.length) return <span>—</span>;
  const opts = optionsOf(config);
  return (
    <ul className="flex flex-wrap gap-1">
      {sel.map((v) => (
        <li key={v} className="rounded-full bg-surface px-2 text-sm">
          {opts.find((o) => o.value === v)?.label || v}
        </li>
      ))}
    </ul>
  );
}

function Edit({ config, value, onChange }: FieldEditProps) {
  const sel = arr(value);
  return (
    <div className="flex flex-col gap-1">
      {optionsOf(config)
        .filter((o) => o.value !== "")
        .map((o) => (
          <label key={o.value} className="flex items-center gap-2 text-sm">
            <Checkbox
              aria-label={o.label || o.value}
              checked={sel.includes(o.value)}
              onCheckedChange={(c) =>
                onChange(
                  c === true
                    ? [...sel, o.value]
                    : sel.filter((x) => x !== o.value),
                )
              }
            />
            {o.label || o.value}
          </label>
        ))}
    </div>
  );
}

/** @brief Multi-select field type. */
export const MultiSelectField: FieldType = {
  key: "multiselect",
  label: "Multi-select",
  View,
  Edit,
  ConfigEditor: OptionsEditor,
};
