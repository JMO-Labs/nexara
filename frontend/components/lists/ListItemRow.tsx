"use client";
/**
 * @file components/lists/ListItemRow.tsx
 * @brief One list item: completion checkbox, field values (registry View),
 *        due date and edit/delete actions.
 */
import { Pencil, Trash2 } from "lucide-react";
import { Checkbox } from "@/components/ui/Checkbox";
import { IconButton } from "@/components/ui/IconButton";
import { fieldRegistry } from "@/lib/lists/fieldRegistry";
import { itemTitle, type ListField } from "@/lib/lists/listFields";
import type { ListItem } from "@/lib/api/listTypes";
import { cn } from "@/lib/utils";

export interface ListItemRowProps {
  item: ListItem;
  fields: ListField[];
  onToggle: (completed: boolean) => void;
  onEdit: () => void;
  onDelete: () => void;
}

/**
 * @brief Render a list item row.
 * @param props see ListItemRowProps
 * @return list item element
 */
export function ListItemRow({
  item,
  fields,
  onToggle,
  onEdit,
  onDelete,
}: ListItemRowProps) {
  const title = itemTitle(item.values, `Item ${item.position + 1}`);
  return (
    <li
      className={cn(
        "flex items-start gap-3 rounded-xl border border-current/15 p-3",
        item.completed && "opacity-70",
      )}
    >
      <Checkbox
        className="mt-1"
        checked={item.completed}
        aria-label={`Complete ${title}`}
        onCheckedChange={(c) => onToggle(c === true)}
      />
      <dl className="grid min-w-0 flex-1 gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
        {fields.map((f) => {
          const View = fieldRegistry.get(f.typeKey)?.View;
          return (
            <div key={f.key} className="flex min-w-0 gap-2">
              <dt className="shrink-0 font-semibold">{f.label}</dt>
              <dd className={cn("truncate", item.completed && "line-through")}>
                {View ? (
                  <View config={f.config} value={item.values[f.key]} />
                ) : (
                  String(item.values[f.key] ?? "—")
                )}
              </dd>
            </div>
          );
        })}
        {item.dueAt && (
          <div className="flex gap-2">
            <dt className="font-semibold">Due</dt>
            <dd>
              <time dateTime={item.dueAt}>
                {new Date(item.dueAt).toLocaleDateString()}
              </time>
            </dd>
          </div>
        )}
      </dl>
      <div className="flex shrink-0 gap-1">
        <IconButton
          size="sm"
          variant="ghost"
          aria-label={`Edit ${title}`}
          onClick={onEdit}
        >
          <Pencil aria-hidden className="size-4" />
        </IconButton>
        <IconButton
          size="sm"
          variant="ghost"
          aria-label={`Delete ${title}`}
          onClick={onDelete}
        >
          <Trash2 aria-hidden className="size-4" />
        </IconButton>
      </div>
    </li>
  );
}
