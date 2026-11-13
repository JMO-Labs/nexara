/**
 * @file lib/lists/fieldTypes/base.tsx
 * @brief Shared types and helpers for list field type modules.
 */
import type { ComponentType } from "react";

export type FieldConfig = Record<string, unknown>;

export interface FieldOption {
  value: string;
  label: string;
}

/** @brief Props for read-only rendering. */
export interface FieldViewProps {
  config: FieldConfig;
  value: unknown;
}

/** @brief Props for editing a cell value. */
export interface FieldEditProps extends FieldViewProps {
  onChange: (value: unknown) => void;
  label?: string;
}

/** @brief Props for the template designer config form. */
export interface FieldConfigEditorProps {
  config: FieldConfig;
  onChange: (config: FieldConfig) => void;
}

/** @brief A registered list field type. */
export interface FieldType {
  key: string;
  label: string;
  View: ComponentType<FieldViewProps>;
  Edit: ComponentType<FieldEditProps>;
  ConfigEditor: ComponentType<FieldConfigEditorProps>;
}

/**
 * @brief Read config.options as a safe option array.
 * @param config field config
 * @return options list
 */
export function optionsOf(config: FieldConfig): FieldOption[] {
  return Array.isArray(config.options) ? (config.options as FieldOption[]) : [];
}

/** @brief ConfigEditor for types needing no config. */
export function NoConfig() {
  return null;
}

/**
 * @brief Build a View that renders text from a value.
 * @param fmt value formatter
 * @return View component
 */
export function textView(fmt: (v: unknown, c: FieldConfig) => string) {
  return function View({ config, value }: FieldViewProps) {
    const s = fmt(value, config);
    return <span>{s || "—"}</span>;
  };
}

export const str = (v: unknown): string => (v == null ? "" : String(v));
