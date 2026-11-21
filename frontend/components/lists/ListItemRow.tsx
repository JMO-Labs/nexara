"use client";
/**
 * @file components/lists/ListItemRow.tsx
 * @brief One list item: completion checkbox, title (first field), secondary
 *        field values (labelled), due date and edit/delete actions.
 */
import { format } from "date-fns";
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
 * @brief Render a field value through its registry View (or as text).
 * @param f field, item values
 * @return value node
 */
function renderValue(f: ListField, item: ListItem) {
  const View = fieldRegistry.get(f.typeKey)?.View;
  return View ? (
    <View config={f.config} value={item.values[f.key]} />
  ) : (
    String(item.values[f.key] ?? "—")
  );
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
  const [first, ...secondary] = fields;
  return (
    <li
      className={cn(
        "glass-item flex items-center gap-3 rounded-[20px] px-4 py-3",
        item.completed && "opacity-70",
      )}
    >
      <Checkbox
        className="size-5 rounded-full"
        checked={item.completed}
        aria-label={`Complete ${title}`}
        onCheckedChange={(c) => onToggle(c === true)}
      />
      <div className="min-w-0 flex-1">
        {first && (
          <p
            className={cn(
              "truncate font-medium",
              item.completed && "line-through",
            )}
          >
            {renderValue(first, item)}
          </p>
        )}
        {(secondary.length > 0 || item.dueAt) && (
          <dl className="mt-0.5 flex flex-wrap gap-x-4 gap-y-0.5 text-sm text-muted">
            {secondary.map((f) => (
              <div key={f.key} className="flex min-w-0 gap-1.5">
                <dt className="shrink-0">{f.label}</dt>
                <dd className="truncate text-ink">{renderValue(f, item)}</dd>
              </div>
            ))}
            {item.dueAt && (
              <div className="flex gap-1.5">
                <dt>Due</dt>
                <dd className="text-ink">
                  <time dateTime={item.dueAt}>
                    {format(new Date(item.dueAt), "EEE, MMM d")}
                  </time>
                </dd>
              </div>
            )}
          </dl>
        )}
      </div>
      <div className="flex shrink-0 gap-1">
        <IconButton
          size="sm"
          variant="glass"
          aria-label={`Edit ${title}`}
          onClick={onEdit}
        >
          <Pencil aria-hidden className="size-4" />
        </IconButton>
        <IconButton
          size="sm"
          variant="glass"
          aria-label={`Delete ${title}`}
          onClick={onDelete}
        >
          <Trash2 aria-hidden className="size-4" />
        </IconButton>
      </div>
    </li>
  );
}
