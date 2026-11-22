"use client";
/**
 * @file components/household/HouseholdMentions.tsx
 * @brief "Mentioned in": posts that @mention a household member or pet,
 *        limited by the server to what the viewer may read.
 */
import { useInfiniteQuery } from "@tanstack/react-query";
import { AtSign } from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { PostCard } from "@/components/feed/PostCard";
import { householdPosts, type HouseholdMember } from "@/lib/api/household";

/** @brief Posts mentioning ``m``, newest first. */
export function HouseholdMentions({ m }: { m: HouseholdMember }) {
  const q = useInfiniteQuery({
    queryKey: ["household", m.id, "posts"],
    queryFn: ({ pageParam }) => householdPosts(m.id, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (p) => p.next_before,
  });
  const posts = q.data?.pages.flatMap((p) => p.posts) ?? [];
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">Mentioned in</h2>
      {q.isLoading ? (
        <Skeleton height={120} rounded="lg" />
      ) : posts.length ? (
        posts.map((p) => <PostCard key={p.id} post={p} />)
      ) : (
        <EmptyState
          compact
          icon={AtSign}
          title={`No posts mention ${m.name} yet`}
          description={
            m.handle
              ? `Type @${m.handle} in a post or comment.`
              : "Type @ in a post or comment and pick them."
          }
        />
      )}
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
    </section>
  );
}
