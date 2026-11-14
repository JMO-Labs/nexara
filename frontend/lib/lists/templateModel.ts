/**
 * @file lib/lists/templateModel.ts
 * @brief Pure state helpers for the list template designer.
 */
import { fieldRegistry } from "./fieldRegistry";
import { optionsOf, type FieldConfig } from "./fieldTypes/base";

export interface TemplateField {
  id: string;
  key: string;
  label: string;
  type_key: string;
  config: FieldConfig;
  position: number;
}

export interface TemplateDraft {
  id?: string;
  name: string;
  fields: TemplateField[];
}

export interface ListTemplate extends TemplateDraft {
  id: string;
  system?: boolean;
}

/**
 * @brief Move a field and renumber positions.
 * @param fields current fields
 * @param activeId dragged id
 * @param overId drop target id
 * @return new array with position = index
 */
export function reorder(
  fields: TemplateField[],
  activeId: string,
  overId: string,
): TemplateField[] {
  const from = fields.findIndex((f) => f.id === activeId);
  const to = fields.findIndex((f) => f.id === overId);
  const next = [...fields];
  if (from >= 0 && to >= 0 && from !== to) {
    const [m] = next.splice(from, 1);
    next.splice(to, 0, m);
  }
  return next.map((f, i) => ({ ...f, position: i }));
}

/** Validation result: template-level name error and per-field errors. */
export interface TemplateErrors {
  name?: string;
  fields: Record<string, string>;
}

/**
 * @brief Validate a template.
 * @param name template name
 * @param fields template fields
 * @return errors; `fields` keyed by field id, empty when valid
 */
export function validateTemplate(
  name: string,
  fields: TemplateField[],
): TemplateErrors {
  const errs: TemplateErrors = { fields: {} };
  if (!name.trim()) errs.name = "Template name is required";
  const seen = new Set<string>();
  for (const f of fields) {
    const key = f.key.trim();
    if (!f.label.trim()) {
      errs.fields[f.id] = "Label is required";
    } else if (!fieldRegistry.get(f.type_key)) {
      errs.fields[f.id] = `Unknown field type: ${f.type_key}`;
    } else if (seen.has(key)) {
      errs.fields[f.id] = "Key must be unique";
    } else if (
      (f.type_key === "select" || f.type_key === "multiselect") &&
      !optionsOf(f.config).some((o) => o.value.trim())
    ) {
      errs.fields[f.id] = "Add at least one option with a value";
    }
    seen.add(key);
  }
  return errs;
}
