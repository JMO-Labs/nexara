"use client";
/**
 * @file lib/lists/fieldTypes/TimeField.tsx
 * @brief Time-of-day field.
 */
import { Input } from "@/components/ui/Input";
import {
  NoConfig,
  str,
  textView,
  type FieldEditProps,
  type FieldType,
} from "./base";

function Edit({ value, onChange, label }: FieldEditProps) {
  return (
    <Input
      type="time"
      aria-label={label ?? "Time"}
      value={str(value)}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

/** @brief Time field type. */
export const TimeField: FieldType = {
  key: "time",
  label: "Time",
  View: textView((v) => str(v)),
  Edit,
  ConfigEditor: NoConfig,
};
