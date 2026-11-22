"use client";
/**
 * @file components/lists/ListActivityFeed.tsx
 * @brief History tab: newest-first "Maya took Folding chairs . 2h ago" lines
 *        with actor avatar and a Load more button.
 */
import { History } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useListActivity } from "@/hooks/useListAssignments";
import type { ListActivity } from "@/lib/api/listTypes";

const VERBS: Record<string, string> = {
  item_added: "added",
  item_edited: "edited",
  item_removed: "removed",
  completed: "completed",
  uncompleted: "reopened",
  taken: "took",
  assigned: "assigned",
  accepted: "accepted",
  declined: "declined",
  released: "gave back",
  unassigned: "unassigned",
  signup_claimed: "signed up for",
  signup_released: "dropped out of",
};

/**
 * @brief Compact relative time: "now", "5m ago", "2h ago", "3d ago".
 * @param iso timestamp
 * @return short label
 */
export function ago(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

/**
 * @brief Sentence for one entry, e.g. "Maya assigned Chairs to Sam".
 * @param a activity entry
 * @return text
 */
export function describeActivity(a: ListActivity): string {
  const who = a.actor?.displayName || "Someone";
  const verb = VERBS[a.action] ?? a.action;
  const item = a.itemTitle || "an item";
  const to = a.targetUser?.displayName;
  if (a.action === "assigned" && to) return `${who} ${verb} ${item} to ${to}`;
  if (a.action === "unassigned" && to)
    return `${who} ${verb} ${to} from ${item}`;
  return `${who} ${verb} ${item}`;
}

/**
 * @brief Activity history for one list.
 * @param props listId
 * @return history section
 */
export function ListActivityFeed({ listId }: { listId: string }) {
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useListActivity(listId);
  const entries = data?.pages.flatMap((p) => p.entries) ?? [];

  if (isLoading) {
    return (
      <div data-testid="activity-loading" className="flex flex-col gap-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={44} rounded="md" />
        ))}
      </div>
    );
  }
  if (entries.length === 0) {
    return (
      <EmptyState
        compact
        icon={History}
        title="No activity yet"
        description="Changes to this list will show up here."
      />
    );
  }
  return (
    <section aria-label="List history" className="flex flex-col gap-3">
      <ul className="flex flex-col gap-2">
        {entries.map((a) => (
          <li
            key={a.id}
            className="glass-item flex items-center gap-3 rounded-[20px] px-4 py-2.5 text-sm"
          >
            <Avatar
              size="sm"
              src={a.actor?.avatarUrl ?? undefined}
              name={a.actor?.displayName}
            />
            <span className="min-w-0 flex-1 truncate">
              {describeActivity(a)}
            </span>
            <time dateTime={a.createdAt} className="shrink-0 text-muted">
              {ago(a.createdAt)}
            </time>
          </li>
        ))}
      </ul>
      {hasNextPage && (
        <Button
          variant="secondary"
          className="self-center"
          loading={isFetchingNextPage}
          onClick={() => void fetchNextPage()}
        >
          Load more
        </Button>
      )}
    </section>
  );
}
