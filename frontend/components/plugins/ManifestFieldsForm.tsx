"use client";
/**
 * @file components/plugins/ManifestFieldsForm.tsx
 * @brief Generic form rendered from a plugin manifest's field specs
 *        (boolean, select, number, string, secret). Each control has a
 *        label and its help text linked via aria-describedby.
 */
import { useId, useState, type FormEvent } from "react";
import { Button, Input, Option, Select, Switch } from "@/components/ui";
import type { FieldSpec } from "@/lib/api/plugins";

export interface ManifestFieldsFormProps {
  fields: Record<string, FieldSpec>;
  /** Current values; secrets arrive masked as `{ set: boolean }`. */
  values: Record<string, unknown>;
  onSubmit: (values: Record<string, unknown>) => void;
  submitLabel?: string;
  pending?: boolean;
}

const isSecretSet = (v: unknown) =>
  typeof v === "object" && v !== null && (v as { set?: unknown }).set === true;

function initial(
  fields: Record<string, FieldSpec>,
  values: Record<string, unknown>,
) {
  const out: Record<string, unknown> = {};
  for (const [k, f] of Object.entries(fields)) {
    const v = k in values ? values[k] : f.default;
    if (f.type === "secret") out[k] = "";
    else if (f.type === "boolean") out[k] = v === true;
    else out[k] = v ?? "";
  }
  return out;
}

/** @brief Same draft with every secret field blanked. */
function clearSecrets(
  fields: Record<string, FieldSpec>,
  draft: Record<string, unknown>,
) {
  const out = { ...draft };
  for (const [k, f] of Object.entries(fields))
    if (f.type === "secret") out[k] = "";
  return out;
}

/**
 * @brief Manifest field form.
 * @param props see ManifestFieldsFormProps
 * @return form element
 */
export function ManifestFieldsForm({
  fields,
  values,
  onSubmit,
  submitLabel = "Save",
  pending,
}: ManifestFieldsFormProps) {
  const uid = useId();
  const [draft, setDraft] = useState(() => initial(fields, values));
  // Fresh values (refetch after a save) mean typed secrets were stored: drop them.
  const [seen, setSeen] = useState(values);
  if (seen !== values) {
    setSeen(values);
    setDraft((d) => clearSecrets(fields, d));
  }
  const set = (k: string, v: unknown) => setDraft((d) => ({ ...d, [k]: v }));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const out: Record<string, unknown> = {};
    for (const [k, f] of Object.entries(fields)) {
      const v = draft[k];
      if (f.type === "number") {
        if (v === "" || v === undefined) continue;
        out[k] = Number(v);
      } else out[k] = v;
    }
    onSubmit(out);
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      {Object.entries(fields).map(([k, f]) => {
        const id = `${uid}-${k}`;
        const helpId = f.help ? `${id}-help` : undefined;
        return (
          <div key={k} className="flex flex-col gap-1.5">
            <label htmlFor={id} className="text-sm font-medium">
              {f.label}
            </label>
            {f.type === "boolean" && (
              <Switch
                id={id}
                aria-describedby={helpId}
                checked={draft[k] === true}
                onCheckedChange={(c) => set(k, c)}
              />
            )}
            {f.type === "select" && (
              <Select
                id={id}
                aria-describedby={helpId}
                value={String(draft[k] ?? "")}
                onValueChange={(v) => set(k, v)}
              >
                {(f.options ?? []).map((o) => (
                  <Option key={o} value={o}>
                    {o}
                  </Option>
                ))}
              </Select>
            )}
            {(f.type === "number" ||
              f.type === "string" ||
              f.type === "secret") && (
              <Input
                id={id}
                aria-describedby={helpId}
                type={
                  f.type === "number"
                    ? "number"
                    : f.type === "secret"
                      ? "password"
                      : "text"
                }
                autoComplete={f.type === "secret" ? "new-password" : "off"}
                min={f.min ?? undefined}
                max={f.max ?? undefined}
                maxLength={
                  f.type === "number" ? undefined : (f.max_length ?? undefined)
                }
                placeholder={
                  f.type === "secret" && isSecretSet(values[k])
                    ? "Saved — leave blank to keep"
                    : undefined
                }
                value={String(draft[k] ?? "")}
                onChange={(e) => set(k, e.target.value)}
              />
            )}
            {f.help && (
              <p id={helpId} className="text-sm text-muted">
                {f.help}
              </p>
            )}
          </div>
        );
      })}
      <div>
        <Button type="submit" loading={pending}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
