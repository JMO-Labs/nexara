"use client";
/**
 * @file components/lists/ListCard.tsx
 * @brief List summary card: color, title, counters, owner and an actions
 *        menu (edit / archive / delete with confirmation).
 */
import { useState } from "react";
import {
  Archive,
  CheckSquare,
  MoreVertical,
  Pencil,
  Trash2,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/shadcn/dropdown-menu";
import { useListDelete } from "@/hooks/useLists";
import { useListArchive } from "@/hooks/useListActions";
import type { List } from "@/lib/api/listTypes";
import { ListEditModal } from "./ListEditModal";

export interface ListCardProps {
  list: List;
  communityId: string;
  /** Display name of the owner. */
  ownerName?: string;
  onOpen?: (list: List) => void;
}

/**
 * @brief List card with actions.
 * @param props see ListCardProps
 * @return article
 */
export function ListCard({
  list,
  communityId,
  ownerName,
  onOpen,
}: ListCardProps) {
  const del = useListDelete(communityId);
  const archive = useListArchive(communityId);
  const [dialog, setDialog] = useState<"edit" | "delete" | null>(null);
  const close = () => setDialog(null);

  return (
    <Card className="relative flex flex-col gap-2 overflow-hidden p-4 pl-5">
      <span
        data-testid="list-color"
        aria-hidden
        className="absolute inset-y-0 left-0 w-1.5"
        style={{ backgroundColor: list.color ?? "var(--color-accent)" }}
      />
      <div className="flex items-start gap-2">
        <h3 className="min-w-0 flex-1 truncate text-base font-semibold">
          {onOpen ? (
            <button
              type="button"
              className="rounded text-left hover:underline focus-visible:outline-2 focus-visible:outline-accent"
              onClick={() => onOpen(list)}
            >
              {list.title}
            </button>
          ) : (
            list.title
          )}
        </h3>
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label="List actions"
            className="rounded-full p-1 hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent"
          >
            <MoreVertical aria-hidden className="size-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => setDialog("edit")}>
              <Pencil aria-hidden className="size-4" /> Edit
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => archive.mutate(list.id)}>
              <Archive aria-hidden className="size-4" /> Archive
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              onSelect={() => setDialog("delete")}
            >
              <Trash2 aria-hidden className="size-4" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {list.description && (
        <p className="line-clamp-2 text-sm opacity-80">{list.description}</p>
      )}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        <span className="inline-flex items-center gap-1">
          <CheckSquare aria-hidden className="size-4" />
          {`${list.completedCount}/${list.itemCount} done`}
        </span>
        <span className="inline-flex items-center gap-1">
          <Users aria-hidden className="size-4" />
          {`${list.signupCount} signups`}
        </span>
        {ownerName && <span className="opacity-80">{`by ${ownerName}`}</span>}
      </div>
      {dialog === "edit" && (
        <ListEditModal
          open
          onClose={close}
          list={list}
          communityId={communityId}
        />
      )}
      <Modal
        open={dialog === "delete"}
        onClose={close}
        title="Delete list?"
        description={`"${list.title}" and its items will be deleted.`}
        size="sm"
        footer={
          <>
            <Button variant="outline" onClick={close}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              loading={del.isPending}
              onClick={() => del.mutate(list.id, { onSuccess: close })}
            >
              OK
            </Button>
          </>
        }
      >
        {null}
      </Modal>
    </Card>
  );
}
