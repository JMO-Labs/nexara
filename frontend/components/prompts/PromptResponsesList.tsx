"use client";
/**
 * @file components/prompts/PromptResponsesList.tsx
 * @brief Paginated list of response posts for a prompt post.
 */
import { AlertCircle } from "lucide-react";
import { useState } from "react";
import { Button, EmptyState, Input, Skeleton } from "@/components/ui";
import { PostCard } from "@/components/feed/PostCard";
import { useInfinitePromptResponses } from "@/hooks/usePromptResponses";

/**
 * @brief Response list with loading, error, empty and load-more states.
 * @param promptPostId prompt post id
 * @return list element
 */
export function PromptResponsesList({
  promptPostId,
}: {
  promptPostId: string;
}) {
  const [search, setSearch] = useState("");
  const q = useInfinitePromptResponses(promptPostId);

  if (q.isLoading) {
    return (
      <div
        role="status"
        aria-label="Loading responses"
        className="flex flex-col gap-4"
      >
        <Skeleton height={160} rounded="lg" />
        <Skeleton height={160} rounded="lg" />
      </div>
    );
  }
  if (q.isError) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="Couldn't load responses"
        description="Check your connection and try again."
        action={
          <Button
            variant="secondary"
            className="min-h-11"
            onClick={() => q.refetch()}
          >
            Retry
          </Button>
        }
      />
    );
  }
  const all = q.data?.pages.flatMap((p) => p.items) ?? [];
  if (all.length === 0) {
    return <EmptyState title="No responses yet." />;
  }
  const term = search.trim().toLowerCase();
  const posts = term
    ? all.filter((p) => (p.content ?? "").toLowerCase().includes(term))
    : all;
  return (
    <div className="flex flex-col gap-4">
      <Input
        type="search"
        label="Search responses"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {posts.length === 0 && <EmptyState title="No matching responses." />}
      {posts.map((post) => (
        <PostCard key={post.id} post={post} />
      ))}
      {q.hasNextPage && (
        <Button
          variant="secondary"
          className="min-h-11 self-center"
          disabled={q.isFetchingNextPage}
          onClick={() => q.fetchNextPage()}
        >
          Load more
        </Button>
      )}
    </div>
  );
}

export default PromptResponsesList;
