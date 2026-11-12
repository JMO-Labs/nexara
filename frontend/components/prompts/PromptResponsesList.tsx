"use client";
/**
 * @file components/prompts/PromptResponsesList.tsx
 * @brief Paginated list of response posts for a prompt post.
 */
import { AlertCircle } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
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
  const posts = q.data?.pages.flatMap((p) => p.items) ?? [];
  if (posts.length === 0) {
    return <EmptyState title="No responses yet." />;
  }
  return (
    <div className="flex flex-col gap-4">
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
