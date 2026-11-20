"use client";
/**
 * @file components/inbox/SavedView.tsx
 * @brief Inbox "Saved" tab: cursor-paginated list of bookmarked posts.
 */
import { Bookmark } from "lucide-react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Button, EmptyState } from "@/components/ui";
import { PostCard } from "@/components/feed/PostCard";
import { listBookmarks } from "@/lib/api/bookmarks";

const LIMIT = 20;

/** @brief Saved tab body (no page header; the Inbox owns it). */
export function SavedView() {
  const q = useInfiniteQuery({
    queryKey: ["bookmarks", "list"],
    queryFn: ({ pageParam }) => listBookmarks(pageParam, LIMIT),
    initialPageParam: null as string | null,
    getNextPageParam: (last) =>
      last.pagination.has_more ? last.pagination.cursor : undefined,
  });
  const items = q.data?.pages.flatMap((p) => p.bookmarks) ?? [];

  return (
    <div className="max-w-3xl">
      {q.isError ? (
        <p role="alert">
          Could not load saved posts.{" "}
          <Button variant="ghost" size="sm" onClick={() => q.refetch()}>
            Retry
          </Button>
        </p>
      ) : q.isLoading ? (
        <p aria-busy="true">Loading…</p>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Bookmark}
          title="Nothing saved yet"
          description="Save posts for later reading!"
        />
      ) : (
        <div className="flex flex-col gap-4">
          {items.map((b) => (
            <PostCard key={b.id} post={{ ...b.post, is_bookmarked: true }} />
          ))}
          {q.hasNextPage ? (
            <Button
              variant="secondary"
              className="self-center"
              disabled={q.isFetchingNextPage}
              onClick={() => q.fetchNextPage()}
            >
              Load more
            </Button>
          ) : null}
        </div>
      )}
    </div>
  );
}
