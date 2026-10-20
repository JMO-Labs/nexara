"use client";
/**
 * @file components/subgroups/create-subgroup/OwnerPicker.tsx
 * @brief Optional "assign to someone else" owner search + selection.
 */
import * as React from "react";
import { Avatar, Button, Input } from "@/components/ui";
import type { SearchResultItem } from "@/lib/api/search";
import type { OwnerUser } from "./useCreateSubgroupForm";

export interface OwnerPickerProps {
  enabled: boolean;
  onToggle: () => void;
  query: string;
  onQueryChange: (q: string) => void;
  suggestions: SearchResultItem[];
  selected: OwnerUser | null;
  onSelect: (u: OwnerUser) => void;
  onClear: () => void;
}

/**
 * @brief Owner assignment control.
 * @param props toggle state, search state and handlers
 * @return control element
 */
export function OwnerPicker({
  enabled,
  onToggle,
  query,
  onQueryChange,
  suggestions,
  selected,
  onSelect,
  onClear,
}: OwnerPickerProps) {
  return (
    <div className="flex flex-col gap-2">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-pressed={enabled}
        onClick={onToggle}
        className="min-h-11 justify-start pl-0"
      >
        {enabled ? "✓ " : ""}Assign to someone else (optional)
      </Button>
      {enabled && (
        <>
          <Input
            label="Owner"
            placeholder="Search for a user…"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
          />
          {suggestions.length > 0 && (
            <ul className="max-h-52 overflow-y-auto rounded-xl border border-current/20">
              {suggestions.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => {
                      onSelect({ id: item.id, display_name: item.title });
                      onQueryChange("");
                    }}
                    className="hover:bg-bg flex min-h-11 w-full items-center gap-2 p-2 text-left text-sm"
                  >
                    <Avatar size="sm" name={item.title} />
                    {item.title}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {selected && (
            <div className="flex items-center justify-between rounded-xl border border-current/20 p-2">
              <div className="flex items-center gap-2 text-sm">
                <Avatar size="sm" name={selected.display_name ?? "User"} />
                {selected.display_name}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="min-h-11 text-destructive"
                onClick={onClear}
              >
                Clear
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default OwnerPicker;
