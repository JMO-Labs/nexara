"use client";
/**
 * @file lib/lists/fieldTypes/SignupField.tsx
 * @brief Read-only signup quantity.
 */
import {
  NoConfig,
  str,
  textView,
  type FieldEditProps,
  type FieldType,
} from "./base";

const View = textView((v) => str(v ?? 0));

function Edit(p: FieldEditProps) {
  return <View config={p.config} value={p.value} />;
}

/** @brief Signup field type; quantity is derived, never edited. */
export const SignupField: FieldType = {
  key: "signup",
  label: "Signup",
  View,
  Edit,
  ConfigEditor: NoConfig,
};
