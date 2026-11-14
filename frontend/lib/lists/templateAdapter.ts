/**
 * @file lib/lists/templateAdapter.ts
 * @brief Convert list templates between the REST shape (camelCase,
 *        `typeKey`) and the designer model (`type_key`, required ids).
 */
import type {
  ListTemplate as ApiTemplate,
  ListTemplateInput,
} from "@/lib/api/listTypes";
import type { ListTemplate, TemplateDraft } from "./templateModel";

/**
 * @brief API template -> designer/gallery model.
 * @param t template from templateApi
 * @return model with fields sorted by position
 */
export function fromApi(t: ApiTemplate): ListTemplate {
  const fields = [...t.fields]
    .sort((a, b) => a.position - b.position)
    .map((f) => ({
      id: f.id ?? f.key,
      key: f.key,
      label: f.label,
      type_key: f.typeKey,
      config: f.config ?? {},
      position: f.position,
    }));
  return { id: t.id, name: t.name, system: t.isShared, fields };
}

/**
 * @brief Designer draft -> create/update payload.
 * @param d draft from TemplateDesigner
 * @return API input; positions renumbered from 0
 */
export function toInput(d: TemplateDraft): ListTemplateInput {
  return {
    name: d.name,
    fields: d.fields.map((f, i) => ({
      key: f.key,
      label: f.label,
      typeKey: f.type_key,
      config: f.config,
      position: i,
    })),
  };
}
