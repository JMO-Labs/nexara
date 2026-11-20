"use client";
/**
 * @file components/feed/AudiencePicker.tsx
 * @brief Compact glass radio-pill audience picker for PostComposer:
 *        Community / A specific group / Just me (+ group select).
 */
import * as React from "react";
import { Option, Select, type ScopeValue } from "@/components/ui";
import { cn } from "@/lib/utils";

export interface AudiencePickerProps {
  value: ScopeValue;
  onChange: (value: ScopeValue) => void;
  subgroups: { id: string; name: string }[];
}

const OPTIONS: { vis: ScopeValue["visibility"]; label: string }[] = [
  { vis: "community", label: "Community" },
  { vis: "subgroup", label: "A specific group" },
  { vis: "private", label: "Just me" },
];

/**
 * @brief Audience radiogroup with arrow-key navigation.
 * @param value current scope
 * @param onChange emits next scope
 * @param subgroups selectable groups
 * @return picker element
 */
export function AudiencePicker({
  value,
  onChange,
  subgroups,
}: AudiencePickerProps) {
  const refs = React.useRef<(HTMLButtonElement | null)[]>([]);
  const pick = (i: number) => {
    const vis = OPTIONS[i].vis;
    onChange({
      visibility: vis,
      subgroup_id: vis === "subgroup" ? value.subgroup_id : null,
    });
    refs.current[i]?.focus();
  };
  const onKey = (e: React.KeyboardEvent, i: number) => {
    const d =
      e.key === "ArrowRight" || e.key === "ArrowDown"
        ? 1
        : e.key === "ArrowLeft" || e.key === "ArrowUp"
          ? -1
          : 0;
    if (!d) return;
    e.preventDefault();
    pick((i + d + OPTIONS.length) % OPTIONS.length);
  };
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div
        role="radiogroup"
        aria-label="Share with"
        className="glass inline-flex items-center gap-1 rounded-full p-1"
      >
        {OPTIONS.map((o, i) => {
          const active = value.visibility === o.vis;
          return (
            <button
              key={o.vis}
              ref={(el) => {
                refs.current[i] = el;
              }}
              type="button"
              role="radio"
              aria-checked={active}
              tabIndex={active ? 0 : -1}
              onClick={() => pick(i)}
              onKeyDown={(e) => onKey(e, i)}
              className={cn(
                "rounded-full px-3 py-1 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2",
                active ? "bg-surface-strong text-bg" : "hover:bg-white/30",
              )}
            >
              {o.label}
            </button>
          );
        })}
      </div>
      {value.visibility === "subgroup" && (
        <Select
          value={value.subgroup_id ?? ""}
          onValueChange={(v) =>
            onChange({ visibility: "subgroup", subgroup_id: v || null })
          }
          placeholder={
            subgroups.length === 0 ? "No groups available" : "Select a group"
          }
          disabled={subgroups.length === 0}
          label="Select a group"
        >
          {subgroups.map((g) => (
            <Option key={g.id} value={g.id}>
              {g.name}
            </Option>
          ))}
        </Select>
      )}
    </div>
  );
}

export default AudiencePicker;
