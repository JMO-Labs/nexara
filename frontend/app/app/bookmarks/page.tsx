"use client";
/**
 * @file app/app/bookmarks/page.tsx
 * @brief Bookmarks page: cursor-paginated list of saved posts.
 */
import { Bookmark } from "lucide-react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Button, EmptyState } from "@/components/ui";
import { PostCard } from "@/components/feed/PostCard";
import { listBookmarks } from "@/lib/api/bookmarks";

const LIMIT = 20;

export default function BookmarksPage() {
  const q = useInfiniteQuery({
    queryKey: ["bookmarks", "list"],
    queryFn: ({ pageParam }) => listBookmarks(pageParam, LIMIT),
    initialPageParam: null as string | null,
    getNextPageParam: (last) =>
      last.pagination.has_more ? last.pagination.cursor : undefined,
  });
  const items = q.data?.pages.flatMap((p) => p.bookmarks) ?? [];

  return (
    <div className="mx-auto max-w-[720px] p-4 md:p-8">
      <h1 className="mb-6 text-3xl font-black tracking-tight">Bookmarks</h1>
      {q.isError ? (
        <p role="alert">
          Could not load bookmarks.{" "}
          <Button variant="ghost" size="sm" onClick={() => q.refetch()}>
            Retry
          </Button>
        </p>
      ) : q.isLoading ? (
        <p aria-busy="true">Loading…</p>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Bookmark}
          title="No bookmarks yet"
          description="No bookmarks yet. Save posts for later reading!"
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
