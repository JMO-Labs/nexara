"use client";
/**
 * @file components/ui/ScopeSelect.tsx
 * @brief Controlled scope picker: community, specific group, or private.
 * WCAG 2.1 AA: labelled radios, keyboard navigable.
 */
import * as React from "react";
import { Select, Option } from "@/components/ui/Select";

export interface ScopeValue {
  visibility: "community" | "subgroup" | "private";
  subgroup_id: string | null;
}

export interface Subgroup {
  id: string;
  name: string;
}

export interface ScopeSelectProps {
  value: ScopeValue;
  onChange: (value: ScopeValue) => void;
  subgroups: Subgroup[];
}

const rowCls =
  "flex cursor-pointer items-center gap-2 rounded-lg p-2 text-sm transition-colors hover:bg-bg";

/**
 * @brief Scope radio group with subgroup dropdown.
 * @param value current scope
 * @param onChange emits next scope
 * @param subgroups selectable groups
 * @return fieldset
 */
export function ScopeSelect({ value, onChange, subgroups }: ScopeSelectProps) {
  return (
    <fieldset className="flex flex-col gap-1.5">
      <legend className="mb-1 text-sm font-semibold">Share with</legend>
      <label className={rowCls}>
        <input
          type="radio"
          name="scope"
          value="community"
          checked={value.visibility === "community"}
          onChange={() =>
            onChange({ visibility: "community", subgroup_id: null })
          }
          aria-label="Community"
        />
        Community
      </label>
      <label className={rowCls}>
        <input
          type="radio"
          name="scope"
          value="subgroup"
          checked={value.visibility === "subgroup"}
          onChange={() =>
            onChange({ visibility: "subgroup", subgroup_id: null })
          }
          aria-label="A specific group"
        />
        A specific group
      </label>
      {value.visibility === "subgroup" && (
        <div className="ml-8">
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
        </div>
      )}
      <label className={rowCls}>
        <input
          type="radio"
          name="scope"
          value="private"
          checked={value.visibility === "private"}
          onChange={() =>
            onChange({ visibility: "private", subgroup_id: null })
          }
          aria-label="Just me (private)"
        />
        Just me (private)
      </label>
    </fieldset>
  );
}

export default ScopeSelect;
