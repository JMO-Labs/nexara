"use client";
/**
 * @file lib/lists/fieldTypes/SelectField.tsx
 * @brief Single-select field.
 */
import { Select, Option } from "@/components/ui/Select";
import {
  optionsOf,
  textView,
  type FieldEditProps,
  type FieldType,
} from "./base";
import { OptionsEditor } from "./OptionsEditor";

function Edit({ config, value, onChange, label }: FieldEditProps) {
  const opts = optionsOf(config).filter((o) => o.value !== "");
  return (
    <Select
      label={label ?? "Select"}
      value={typeof value === "string" && value ? value : undefined}
      onValueChange={onChange}
    >
      {opts.map((o) => (
        <Option key={o.value} value={o.value}>
          {o.label || o.value}
        </Option>
      ))}
    </Select>
  );
}

/** @brief Select field type. */
export const SelectField: FieldType = {
  key: "select",
  label: "Select",
  View: textView((v, c) => {
    const o = optionsOf(c).find((x) => x.value === v);
    return o ? o.label || o.value : "";
  }),
  Edit,
  ConfigEditor: OptionsEditor,
};
