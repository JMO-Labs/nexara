"use client";
/**
 * @file components/feed/PluginComposerFlags.tsx
 * @brief Per-post flags contributed by enabled plugins, shown in the
 *        composer. Value shape matches the API: {plugin_id: {flag: value}}.
 */
import { useId } from "react";
import { Input, Option, Select, Switch } from "@/components/ui";
import { usePluginUi } from "@/hooks/usePluginUi";
import type { FieldSpec } from "@/lib/api/plugins";

export type PluginFlags = Record<string, Record<string, unknown>>;

interface Props {
  value: PluginFlags;
  onChange: (v: PluginFlags) => void;
}

function Flag({
  spec,
  value,
  onChange,
}: {
  spec: FieldSpec;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const id = useId();
  if (spec.type === "boolean")
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Switch id={id} checked={value === true} onCheckedChange={onChange} />
        <label htmlFor={id} className="text-sm">
          {spec.label}
        </label>
      </div>
    );
  return (
    <div className="flex flex-wrap items-center gap-2">
      <label htmlFor={id} className="min-w-0 text-sm">
        {spec.label}
      </label>
      {spec.type === "select" ? (
        <Select id={id} value={String(value ?? "")} onValueChange={onChange}>
          {(spec.options ?? []).map((o) => (
            <Option key={o} value={o}>
              {o}
            </Option>
          ))}
        </Select>
      ) : (
        <Input
          id={id}
          type={spec.type === "number" ? "number" : "text"}
          value={String(value ?? "")}
          onChange={(e) =>
            onChange(
              spec.type === "number" && e.target.value !== ""
                ? Number(e.target.value)
                : spec.type === "number"
                  ? undefined
                  : e.target.value,
            )
          }
        />
      )}
    </div>
  );
}

/**
 * @brief Flag controls for every enabled plugin; renders nothing if none.
 * @param value current flags
 * @param onChange receives the full updated flags object
 * @return controls or null
 */
export function PluginComposerFlags({ value, onChange }: Props) {
  const { data = [] } = usePluginUi();
  const plugins = data.filter((p) => Object.keys(p.composer_flags).length > 0);
  if (!plugins.length) return null;
  return (
    <div className="mb-2 flex flex-col gap-1.5">
      {plugins.map((p) =>
        Object.entries(p.composer_flags).map(([k, spec]) => (
          <Flag
            key={`${p.plugin_id}.${k}`}
            spec={spec}
            value={value[p.plugin_id]?.[k] ?? spec.default}
            onChange={(v) => {
              const { [k]: _drop, ...rest } = value[p.plugin_id] ?? {};
              void _drop;
              const next = v === undefined ? rest : { ...rest, [k]: v };
              const { [p.plugin_id]: _p, ...others } = value;
              void _p;
              onChange(
                Object.keys(next).length
                  ? { ...others, [p.plugin_id]: next }
                  : others,
              );
            }}
          />
        )),
      )}
    </div>
  );
}
