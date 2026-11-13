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

/**
 * @brief Validate a template; returns errors keyed by field id (or "name").
 * @param name template name
 * @param fields template fields
 * @return error map, empty when valid
 */
export function validateTemplate(
  name: string,
  fields: TemplateField[],
): Record<string, string> {
  const errs: Record<string, string> = {};
  if (!name.trim()) errs.name = "Template name is required";
  for (const f of fields) {
    if (!f.label.trim()) {
      errs[f.id] = "Label is required";
    } else if (!fieldRegistry.get(f.type_key)) {
      errs[f.id] = `Unknown field type: ${f.type_key}`;
    } else if (
      (f.type_key === "select" || f.type_key === "multiselect") &&
      !optionsOf(f.config).some((o) => o.value.trim())
    ) {
      errs[f.id] = "Add at least one option with a value";
    }
  }
  return errs;
}
