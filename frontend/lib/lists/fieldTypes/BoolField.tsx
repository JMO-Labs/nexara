"use client";
/**
 * @file lib/lists/fieldTypes/BoolField.tsx
 * @brief Boolean field (checkbox).
 */
import { Checkbox } from "@/components/ui/Checkbox";
import {
  NoConfig,
  type FieldEditProps,
  type FieldType,
  type FieldViewProps,
} from "./base";

function View({ value }: FieldViewProps) {
  return <span>{value ? "Yes" : "No"}</span>;
}

function Edit({ value, onChange, label }: FieldEditProps) {
  return (
    <Checkbox
      aria-label={label ?? "Value"}
      checked={value === true}
      onCheckedChange={(c) => onChange(c === true)}
    />
  );
}

/** @brief Bool field type. */
export const BoolField: FieldType = {
  key: "bool",
  label: "Yes/No",
  View,
  Edit,
  ConfigEditor: NoConfig,
};
