"use client";
/**
 * @file components/subgroups/hub/PostsTab.tsx
 * @brief Posts tab: feed of posts filtered by subgroup.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { PostComposer } from "@/components/feed/PostComposer";
import { PostCard } from "@/components/feed/PostCard";
import { useFeed } from "@/hooks/usePosts";
import type { SubgroupDetail } from "@/lib/api/subgroups";

export interface PostsTabProps {
  subgroup: SubgroupDetail;
}

export function PostsTab({ subgroup }: PostsTabProps) {
  const router = useRouter();
  const {
    data,
    isLoading,
    isError,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useFeed({ subgroup_id: subgroup.id });

  const sentinelRef = React.useRef<HTMLDivElement | null>(null);
  React.useEffect(() => {
    const el = sentinelRef.current;
    if (!el || !hasNextPage) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isFetchingNextPage) fetchNextPage();
      },
      { rootMargin: "300px" },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const posts = React.useMemo(
    () => (data?.pages ?? []).flatMap((p) => p.items),
    [data],
  );

  return (
    <div className="flex flex-col gap-4">
      {subgroup.my_role && (
        <PostComposer defaultSubgroupId={subgroup.id} onPosted={() => {}} />
      )}
      {isLoading ? (
        <div className="flex flex-col gap-4">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={180} />
          ))}
        </div>
      ) : isError ? (
        <EmptyState
          title="Couldn't load posts"
          description={
            error instanceof Error ? error.message : "Try again in a moment."
          }
          action={
            <Button onClick={() => window.location.reload()}>Retry</Button>
          }
        />
      ) : posts.length === 0 ? (
        <EmptyState
          title="Quiet here"
          description="Be the first to share something with your community."
        />
      ) : (
        <>
          <div className="flex flex-col gap-4">
            {posts.map((p) => (
              <div key={p.id}>
                <PostCard
                  post={p}
                  truncateBody
                  onOpen={(id) => router.push(`/app/post/${id}`)}
                />
              </div>
            ))}
            <div ref={sentinelRef} aria-hidden className="h-px" />
            {isFetchingNextPage ? <Skeleton height={120} /> : null}
            {!hasNextPage && posts.length > 0 ? (
              <p className="py-4 text-center text-xs text-muted">
                You&apos;re all caught up.
              </p>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}

export default PostsTab;
