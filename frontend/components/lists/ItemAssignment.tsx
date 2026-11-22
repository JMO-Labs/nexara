"use client";
/**
 * @file components/lists/ItemAssignment.tsx
 * @brief Assignee chip + per-role actions for one list item: take, assign,
 *        accept/decline, give back and unassign.
 */
import { Check, HandHelping, Undo2, UserMinus, X } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { ItemAssignContext } from "@/hooks/useListAssignments";
import type { ListItem } from "@/lib/api/listTypes";
import { AssignPicker } from "./AssignPicker";

export interface ItemAssignmentProps {
  item: ListItem;
  /** Display title used in aria-labels. */
  title: string;
  ctx: ItemAssignContext;
}

/**
 * @brief Render assignment status and the actions the viewer may take.
 * @param props see ItemAssignmentProps
 * @return assignment controls
 */
export function ItemAssignment({ item, title, ctx }: ItemAssignmentProps) {
  const { viewerId, canManage, actions: a } = ctx;
  const who = item.assignee;
  const mine = Boolean(who && who.id === viewerId);
  const pending = item.assignmentStatus === "pending";
  const btn = { size: "sm", variant: "secondary", disabled: a.busy } as const;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {who && (
        <span className="flex items-center gap-1.5 text-sm">
          <Avatar
            size="sm"
            src={who.avatarUrl ?? undefined}
            name={who.displayName}
          />
          <span className="max-w-32 truncate">{who.displayName}</span>
          <Badge tone={pending ? "sun" : "leaf"}>
            {pending ? "Pending" : "Accepted"}
          </Badge>
        </span>
      )}
      {!who && !item.completed && (
        <Button
          {...btn}
          aria-label={`I'll take ${title}`}
          onClick={() => a.take(item.id)}
        >
          <HandHelping aria-hidden className="size-4" /> I&apos;ll take it
        </Button>
      )}
      {mine && pending && (
        <>
          <Button
            {...btn}
            aria-label={`Accept ${title}`}
            onClick={() => a.accept(item.id)}
          >
            <Check aria-hidden className="size-4" /> Accept
          </Button>
          <Button
            {...btn}
            aria-label={`Decline ${title}`}
            onClick={() => a.decline(item.id)}
          >
            <X aria-hidden className="size-4" /> Decline
          </Button>
        </>
      )}
      {mine && !pending && (
        <Button
          {...btn}
          aria-label={`Give back ${title}`}
          onClick={() => a.release(item.id)}
        >
          <Undo2 aria-hidden className="size-4" /> Give back
        </Button>
      )}
      {canManage && !item.completed && (
        <AssignPicker
          title={title}
          disabled={a.busy}
          onPick={(uid) => a.assign(item.id, uid)}
        />
      )}
      {canManage && who && (
        <Button
          {...btn}
          aria-label={`Unassign ${title}`}
          onClick={() => a.unassign(item.id)}
        >
          <UserMinus aria-hidden className="size-4" /> Unassign
        </Button>
      )}
    </div>
  );
}
