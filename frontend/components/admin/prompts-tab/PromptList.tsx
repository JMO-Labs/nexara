"use client";
/**
 * @file components/admin/prompts-tab/PromptList.tsx
 * @brief Compact selectable list of prompts with enable toggles.
 */
import { Plus } from "lucide-react";
import { Badge, Button, Switch } from "@/components/ui";
import type { PromptResponse } from "@/lib/api/prompts";
import { cn } from "@/lib/utils";
import { frequencyTone } from "./constants";

interface Props {
  prompts: PromptResponse[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
  onNew: () => void;
}

/**
 * @brief Left pane of the prompts tab.
 * @param props prompts, selection, and callbacks
 * @return list element
 */
export function PromptList({
  prompts,
  selectedId,
  onSelect,
  onToggle,
  onNew,
}: Props) {
  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Prompts</h2>
        <Button size="sm" onClick={onNew}>
          <Plus className="size-4" aria-hidden="true" />
          New
        </Button>
      </div>
      {prompts.length === 0 && <p className="text-muted">No prompts yet</p>}
      <ul className="flex flex-col gap-2">
        {prompts.map((p) => (
          <li
            key={p.id}
            className={cn(
              "flex items-start gap-3 rounded-2xl p-3",
              selectedId === p.id
                ? "bg-surface-strong text-accent"
                : "bg-surface",
            )}
          >
            <Switch
              size="sm"
              checked={p.is_enabled}
              onCheckedChange={() => onToggle(p.id, p.is_enabled)}
              aria-label={`Toggle ${p.title}`}
              className="mt-1"
            />
            <button
              type="button"
              onClick={() => onSelect(p.id)}
              aria-pressed={selectedId === p.id}
              className="flex min-h-11 min-w-0 flex-1 flex-col items-start gap-1 text-left outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <span
                className={cn("font-semibold", !p.is_enabled && "opacity-60")}
              >
                {p.title}
              </span>
              <span className="flex items-center gap-2">
                <Badge tone={frequencyTone(p.frequency_type)}>
                  {p.frequency_type.replace(/_/g, " ")}
                </Badge>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
