"use client";
/**
 * @file components/members/PeopleDirectory.tsx
 * @brief People directory: search, filter, grid of person cards, load more.
 */
import * as React from "react";
import { Users } from "lucide-react";
import {
  PageHeader,
  Toolbar,
  SearchField,
  Segmented,
} from "@/components/ui/page";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui";
import { PersonCard } from "@/components/members/PersonCard";
import { useDirectory } from "@/hooks/useMembers";
import type { DirectoryFilter } from "@/lib/api/users";

const OPTIONS: { value: DirectoryFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "online", label: "Online" },
  { value: "groups", label: "My groups" },
];

/**
 * @brief Directory page body.
 * @param props embedded hides the PageHeader (used inside Community)
 * @return header, toolbar and results grid
 */
export function PeopleDirectory({ embedded = false }: { embedded?: boolean }) {
  const [q, setQ] = React.useState("");
  const [filter, setFilter] = React.useState<DirectoryFilter>("all");
  const query = useDirectory(q.trim(), filter);
  const people = query.data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <>
      {!embedded && (
        <PageHeader
          title="People"
          description="Everyone in your community, and the groups you share."
        />
      )}
      <Toolbar>
        <SearchField
          value={q}
          onChange={setQ}
          placeholder="Search people"
          label="Search people"
          debounceMs={250}
        />
        <Segmented
          label="Filter people"
          options={OPTIONS}
          value={filter}
          onChange={setFilter}
        />
      </Toolbar>
      <div className="mt-4" aria-busy={query.isLoading}>
        {query.isLoading ? (
          <div
            data-testid="people-skeleton"
            className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          >
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="glass h-40 animate-pulse rounded-[28px]"
              />
            ))}
          </div>
        ) : query.isError ? (
          <EmptyState
            icon={Users}
            title="Couldn't load people"
            action={<Button onClick={() => query.refetch()}>Try again</Button>}
          />
        ) : people.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No one found"
            description="Try a different search or filter."
          />
        ) : (
          <>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {people.map((p) => (
                <li key={p.user_id} className="flex [&>article]:w-full">
                  <PersonCard person={p} />
                </li>
              ))}
            </ul>
            {query.hasNextPage && (
              <div className="mt-4 flex justify-center">
                <Button
                  variant="secondary"
                  onClick={() => query.fetchNextPage()}
                  loading={query.isFetchingNextPage}
                >
                  Load more
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
