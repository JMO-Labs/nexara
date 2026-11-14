/**
 * @file lib/lists/listFields.ts
 * @brief Normalise a list's raw field_schema JSON into typed field rows.
 */
import type { FieldSchema } from "@/lib/api/listTypes";

/** @brief One field definition of a list. */
export interface ListField {
  key: string;
  label: string;
  typeKey: string;
  required: boolean;
  config: Record<string, unknown>;
}

/**
 * @brief Parse field_schema rows (snake or camel keys); drop invalid rows.
 * @param schema raw schema
 * @return fields in schema order
 */
export function fieldsOf(schema: FieldSchema | undefined): ListField[] {
  return (schema ?? []).flatMap((r) => {
    const { key, label } = r;
    const typeKey = r.type_key ?? r.typeKey;
    if (typeof key !== "string" || typeof typeKey !== "string") return [];
    return [
      {
        key,
        label: typeof label === "string" ? label : key,
        typeKey,
        required: r.required === true,
        config: (r.config as Record<string, unknown> | undefined) ?? {},
      },
    ];
  });
}

/**
 * @brief Human title for an item: first non-empty string value.
 * @param values item values
 * @param fallback used when nothing fits
 * @return title
 */
export function itemTitle(
  values: Record<string, unknown>,
  fallback: string,
): string {
  const v = Object.values(values).find(
    (x) => typeof x === "string" && x.trim() !== "",
  );
  return (v as string | undefined) ?? fallback;
}
