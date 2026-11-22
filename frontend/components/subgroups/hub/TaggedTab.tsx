"use client";
/**
 * @file components/subgroups/hub/TaggedTab.tsx
 * @brief Group "Tagged" tab: posts that @-tag this group, limited by the
 *        server to what the viewer may read.
 */
import { useInfiniteQuery } from "@tanstack/react-query";
import { AtSign } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { PostCard } from "@/components/feed/PostCard";
import { getGroupTagged } from "@/lib/api/tags";
import type { SubgroupDetail } from "@/lib/api/subgroups";

/**
 * @brief Tagged posts for a group.
 * @param subgroup group detail
 * @return tab body
 */
export function TaggedTab({ subgroup }: { subgroup: SubgroupDetail }) {
  const q = useInfiniteQuery({
    queryKey: ["tagged", "group", subgroup.id],
    queryFn: ({ pageParam }) => getGroupTagged(subgroup.id, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (p) => p.next_before,
  });
  const posts = q.data?.pages.flatMap((p) => p.posts) ?? [];
  if (q.isLoading) return <Skeleton height={160} rounded="lg" />;
  if (!posts.length)
    return (
      <EmptyState
        compact
        icon={AtSign}
        title={`No posts tag @${subgroup.slug} yet`}
        description="Type @ in a post or comment and pick the group to notify everyone in it."
      />
    );
  return (
    <div className="mx-auto flex w-full max-w-[760px] flex-col gap-4">
      {posts.map((p) => (
        <PostCard key={p.id} post={p} />
      ))}
      {q.hasNextPage && (
        <Button
          variant="ghost"
          size="sm"
          className="self-center"
          loading={q.isFetchingNextPage}
          onClick={() => void q.fetchNextPage()}
        >
          Load more
        </Button>
      )}
    </div>
  );
}
