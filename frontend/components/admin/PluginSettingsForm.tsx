"use client";
/**
 * @file components/admin/PluginSettingsForm.tsx
 * @brief Dynamic settings form built from a plugin manifest settings schema.
 */
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Button, Input, Switch } from "@/components/ui";
import { useUpdatePluginSettings, type SettingSpec } from "@/lib/api/plugins";

type Draft = Record<string, string | boolean>;

const initial = (
  schema: Record<string, SettingSpec>,
  values: Record<string, unknown>,
): Draft =>
  Object.fromEntries(
    Object.entries(schema).map(([k, s]) => {
      const v = values[k] ?? s.default;
      return [
        k,
        s.type === "boolean" ? Boolean(v) : v == null ? "" : String(v),
      ];
    }),
  );

/**
 * @brief Validate a draft against the schema.
 * @return map of field key to error message (empty when valid)
 */
export function validateSettings(
  schema: Record<string, SettingSpec>,
  draft: Draft,
): Record<string, string> {
  const errs: Record<string, string> = {};
  for (const [k, s] of Object.entries(schema)) {
    if (s.type === "boolean") continue;
    const raw = String(draft[k] ?? "").trim();
    if (raw === "") {
      if (s.required) errs[k] = `${s.label} is required`;
    } else if (s.type === "integer" && !/^-?\d+$/.test(raw)) {
      errs[k] = `${s.label} must be a whole number`;
    } else if (s.type === "number" && !Number.isFinite(Number(raw))) {
      errs[k] = `${s.label} must be a number`;
    }
  }
  return errs;
}

/**
 * @brief Settings form.
 * @param pluginId plugin id
 * @param schema manifest settings schema
 * @param values current values (secrets arrive masked)
 * @return form element
 */
export function PluginSettingsForm({
  pluginId,
  schema,
  values,
}: {
  pluginId: string;
  schema: Record<string, SettingSpec>;
  values: Record<string, unknown>;
}) {
  const [draft, setDraft] = useState<Draft>(() => initial(schema, values));
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const [shown, setShown] = useState<Set<string>>(new Set());
  const [errors, setErrors] = useState<Record<string, string>>({});
  const save = useUpdatePluginSettings(pluginId);

  const set = (k: string, v: string | boolean) => {
    setDraft((d) => ({ ...d, [k]: v }));
    setTouched((t) => new Set(t).add(k));
  };
  const toggleShown = (k: string) =>
    setShown((s) => {
      const n = new Set(s);
      if (!n.delete(k)) n.add(k);
      return n;
    });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validateSettings(schema, draft);
    setErrors(errs);
    if (Object.keys(errs).length) return;
    const out: Record<string, unknown> = {};
    for (const [k, s] of Object.entries(schema)) {
      const v = draft[k];
      if (s.secret && !touched.has(k)) continue;
      if (s.type === "boolean") out[k] = v;
      else if (String(v).trim() === "") continue;
      else out[k] = s.type === "string" ? v : Number(v);
    }
    save.mutate(out);
  };

  const keys = Object.keys(schema);
  if (keys.length === 0)
    return <p className="text-sm text-muted">This plugin has no settings.</p>;

  return (
    <form onSubmit={submit} noValidate className="flex max-w-lg flex-col gap-4">
      {keys.map((k) => {
        const s = schema[k];
        if (s.type === "boolean")
          return (
            <div key={k} className="flex items-center justify-between gap-3">
              <span id={`set-${k}`} className="text-sm font-semibold">
                {s.label}
              </span>
              <Switch
                aria-labelledby={`set-${k}`}
                checked={draft[k] as boolean}
                onCheckedChange={(v) => set(k, v)}
              />
            </div>
          );
        const hidden = s.secret && !shown.has(k);
        return (
          <div key={k} className="flex items-start gap-2">
            <div className="flex-1">
              <Input
                label={s.label}
                type={
                  hidden ? "password" : s.type === "string" ? "text" : "number"
                }
                step={s.type === "number" ? "any" : undefined}
                value={draft[k] as string}
                error={errors[k]}
                required={s.required}
                autoComplete="off"
                onChange={(e) => set(k, e.target.value)}
              />
            </div>
            {s.secret && (
              <Button
                type="button"
                variant="ghost"
                className="mt-7"
                aria-label={`${shown.has(k) ? "Hide" : "Show"} ${s.label}`}
                aria-pressed={shown.has(k)}
                onClick={() => toggleShown(k)}
              >
                {shown.has(k) ? (
                  <EyeOff className="size-4" />
                ) : (
                  <Eye className="size-4" />
                )}
              </Button>
            )}
          </div>
        );
      })}
      <Button type="submit" loading={save.isPending} className="self-start">
        Save settings
      </Button>
    </form>
  );
}

export default PluginSettingsForm;
