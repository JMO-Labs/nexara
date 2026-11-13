"use client";
/**
 * @file lib/lists/fieldTypes/UserPullField.tsx
 * @brief Read-only field pulling a user attribute.
 */
import { Input } from "@/components/ui/Input";
import {
  str,
  textView,
  type FieldConfigEditorProps,
  type FieldEditProps,
  type FieldType,
} from "./base";

const View = textView((v) => str(v));

function Edit(p: FieldEditProps) {
  return <View config={p.config} value={p.value} />;
}

function ConfigEditor({ config, onChange }: FieldConfigEditorProps) {
  return (
    <Input
      label="User attribute"
      hint="Which user attribute to pull, e.g. display_name"
      value={str(config.source)}
      onChange={(e) => onChange({ ...config, source: e.target.value })}
    />
  );
}

/** @brief User-pull field type. */
export const UserPullField: FieldType = {
  key: "user_pull",
  label: "User pull",
  View,
  Edit,
  ConfigEditor,
};
