"use client";
/**
 * @file components/home/widgets/MyGroupsWidget.tsx
 * @brief Up to 6 of the user's groups as links, plus "View all" when more.
 */
import * as React from "react";
import Link from "next/link";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { Avatar, EmptyState, Skeleton } from "@/components/ui";

const LINK =
  "flex items-center gap-2 rounded-xl px-2 py-1.5 text-sm font-semibold text-ink hover:bg-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

/**
 * @brief My groups widget body.
 * @return group links, skeleton or empty state
 */
export function MyGroupsWidget() {
  const { data, isLoading } = useSubgroupList();
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={36} rounded="md" />
        ))}
      </div>
    );
  }
  const all = (data ?? []).filter((sg) => sg.my_role !== null);
  if (all.length === 0) {
    return (
      <EmptyState
        compact
        title="No groups yet"
        description="Join a group to see it here."
      />
    );
  }
  return (
    <ul className="flex flex-col gap-1">
      {all.slice(0, 6).map((sg) => (
        <li key={sg.id}>
          <Link
            href={`/app/subgroups/${sg.slug}`}
            aria-label={`Go to ${sg.name}`}
            className={LINK}
          >
            <Avatar name={sg.name} src={sg.avatar_url ?? undefined} size="sm" />
            <span className="truncate">{sg.name}</span>
          </Link>
        </li>
      ))}
      {all.length > 6 && (
        <li>
          <Link
            href="/app/subgroups"
            aria-label="View all groups"
            className={`${LINK} text-muted`}
          >
            View all
          </Link>
        </li>
      )}
    </ul>
  );
}

export default MyGroupsWidget;
