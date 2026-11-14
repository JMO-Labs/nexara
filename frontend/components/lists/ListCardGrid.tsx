"use client";
/**
 * @file components/lists/ListCardGrid.tsx
 * @brief Responsive grid of ListCards for a community (useLists).
 */
import { ListChecks } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useLists } from "@/hooks/useLists";
import type { List } from "@/lib/api/listTypes";
import { ListCard } from "./ListCard";

export interface ListCardGridProps {
  communityId: string;
  onOpen?: (list: List) => void;
  /** Resolve an owner id to a display name. */
  ownerName?: (ownerId: string) => string | undefined;
  /** Only show lists with this visibility; all when omitted. */
  visibility?: string;
  /** Sort order; default most recently updated first. */
  sortBy?: ListSort;
}

export type ListSort = "updated" | "created" | "title";

const byDesc = (k: "updatedAt" | "createdAt") => (a: List, b: List) =>
  b[k].localeCompare(a[k]);
const SORTERS: Record<ListSort, (a: List, b: List) => number> = {
  updated: byDesc("updatedAt"),
  created: byDesc("createdAt"),
  title: (a, b) => a.title.localeCompare(b.title),
};

const GRID = "grid gap-3 sm:grid-cols-2 lg:grid-cols-3";

/**
 * @brief Lists overview grid.
 * @param props see ListCardGridProps
 * @return grid
 */
export function ListCardGrid({
  communityId,
  onOpen,
  ownerName,
  visibility,
  sortBy = "updated",
}: ListCardGridProps) {
  const { data, isLoading } = useLists(communityId);
  if (isLoading) {
    return (
      <div data-testid="list-cards-loading" className={GRID}>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={120} rounded="lg" />
        ))}
      </div>
    );
  }
  const lists = (data?.lists ?? [])
    .filter((l) => !visibility || l.visibility === visibility)
    .sort(SORTERS[sortBy]);
  if (lists.length === 0) {
    return <EmptyState icon={ListChecks} title="No lists yet" compact />;
  }
  return (
    <div className={GRID}>
      {lists.map((l) => (
        <ListCard
          key={l.id}
          list={l}
          communityId={communityId}
          onOpen={onOpen}
          ownerName={ownerName?.(l.ownerId)}
        />
      ))}
    </div>
  );
}
