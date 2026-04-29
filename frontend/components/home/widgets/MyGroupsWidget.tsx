"use client";
/**
 * @file components/home/widgets/MyGroupsWidget.tsx
 * @brief Compact tile grid of the user's subgroups (up to 6).
 *        Each tile links to the subgroup hub page.
 */
import * as React from "react";
import Link from "next/link";
import Typography from "@mui/joy/Typography";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { EmptyState, Skeleton } from "@/components/ui";
import type { WidgetContext } from "@/lib/widgets/registry";

export function MyGroupsWidget(_: WidgetContext) {
  const { data, isLoading } = useSubgroupList();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} height={72} rounded="md" />
        ))}
      </div>
    );
  }

  const allGroups = (data ?? []).filter((sg) => sg.my_role !== null);
  const groups = allGroups.slice(0, 6);
  const hasMore = allGroups.length > 6;

  if (groups.length === 0) {
    return (
      <EmptyState
        title="No groups yet"
        description="Join a group to see it here."
      />
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {groups.map((sg) => (
        <Link
          key={sg.id}
          href={`/app/subgroups/${sg.slug}`}
          aria-label={`Go to ${sg.name}`}
          className="flex flex-col items-center gap-1.5 p-3 rounded-xl border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 transition-colors text-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)]"
        >
          {sg.avatar_url ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={sg.avatar_url}
              alt=""
              className="w-10 h-10 rounded-full object-cover"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
              <span className="text-indigo-600 dark:text-indigo-400 text-sm font-bold">
                {sg.name.charAt(0).toUpperCase()}
              </span>
            </div>
          )}
          <Typography
            level="body-xs"
            fontWeight="md"
            noWrap
            sx={{ maxWidth: "100%" }}
          >
            {sg.name}
          </Typography>
        </Link>
      ))}
      {hasMore && (
        <Link
          href="/app/subgroups"
          aria-label="View all groups"
          className="flex flex-col items-center gap-1.5 p-3 rounded-xl border border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800/60 transition-colors text-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)]"
        >
          <div className="w-10 h-10 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center">
            <span className="text-neutral-500 dark:text-neutral-400 text-lg font-bold">
              +
            </span>
          </div>
          <Typography
            level="body-xs"
            fontWeight="md"
            noWrap
            sx={{ maxWidth: "100%" }}
          >
            View all
          </Typography>
        </Link>
      )}
    </div>
  );
}

export default MyGroupsWidget;
