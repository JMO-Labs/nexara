"use client";
/**
 * @file components/lists/ListGrid.tsx
 * @brief Items of one list via the useListItems infinite query: skeletons,
 *        empty state, "Load more" pagination and item create/edit/delete.
 */
import { useState } from "react";
import { ListPlus, Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useListItemComplete, useListItems } from "@/hooks/useLists";
import { useListItemDelete } from "@/hooks/useListActions";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { fieldsOf } from "@/lib/lists/listFields";
import type { FieldSchema, ListItem } from "@/lib/api/listTypes";
import { ListItemRow } from "./ListItemRow";
import { ListItemEditModal } from "./ListItemEditModal";

export interface ListGridProps {
  listId: string;
  fieldSchema: FieldSchema;
}

/** Modal state: closed, creating (null) or editing an item. */
type Editing = { item: ListItem | null } | undefined;

/**
 * @brief Paginated list items with actions.
 * @param props see ListGridProps
 * @return items section
 */
export function ListGrid({ listId, fieldSchema }: ListGridProps) {
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useListItems(listId);
  const complete = useListItemComplete(listId);
  const remove = useListItemDelete(listId);
  const confirm = useConfirmDialog((s) => s.confirm);
  const [editing, setEditing] = useState<Editing>();
  const fields = fieldsOf(fieldSchema);
  const items = data?.pages.flatMap((p) => p.items) ?? [];

  const onDelete = async (it: ListItem) => {
    const ok = await confirm({
      title: "Delete item?",
      message: "This item will be removed from the list.",
      confirmLabel: "Delete",
      tone: "danger",
    });
    if (ok) remove.mutate(it.id);
  };

  const modal = editing && (
    <ListItemEditModal
      open
      onClose={() => setEditing(undefined)}
      listId={listId}
      fields={fields}
      item={editing.item ?? undefined}
      nextPosition={items.length}
    />
  );

  if (isLoading) {
    return (
      <div data-testid="list-grid-loading" className="flex flex-col gap-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={56} rounded="md" />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <>
        <EmptyState
          compact
          icon={ListPlus}
          title="No items yet, create one"
          action={
            <Button onClick={() => setEditing({ item: null })}>Add item</Button>
          }
        />
        {modal}
      </>
    );
  }

  return (
    <section aria-label="List items" className="flex flex-col gap-3">
      <div className="flex justify-end">
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setEditing({ item: null })}
        >
          <Plus aria-hidden className="size-4" /> New item
        </Button>
      </div>
      <ul className="flex flex-col gap-2">
        {items.map((it) => (
          <ListItemRow
            key={it.id}
            item={it}
            fields={fields}
            onToggle={(completed) =>
              complete.mutate({ itemId: it.id, completed })
            }
            onEdit={() => setEditing({ item: it })}
            onDelete={() => void onDelete(it)}
          />
        ))}
      </ul>
      <Button
        variant="outline"
        className="self-center"
        disabled={!hasNextPage}
        loading={isFetchingNextPage}
        onClick={() => void fetchNextPage()}
      >
        Load more
      </Button>
      {modal}
    </section>
  );
}
