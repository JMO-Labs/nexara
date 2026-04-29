"use client";
/**
 * @file components/subgroups/hub/PostsTab.tsx
 * @brief Posts tab: feed of posts filtered by subgroup.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import { AnimatePresence, motion } from "framer-motion";
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
    <Stack spacing={2}>
      {subgroup.my_role && (
        <PostComposer subgroupId={subgroup.id} onPosted={() => {}} />
      )}
      {isLoading ? (
        <Stack spacing={2}>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={180} />
          ))}
        </Stack>
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
        <AnimatePresence>
          <Stack spacing={2}>
            {posts.map((p) => (
              <motion.div
                key={p.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15, ease: "easeOut" }}
              >
                <PostCard
                  post={p}
                  truncateBody
                  onOpen={(id) => router.push(`/app/post/${id}`)}
                />
              </motion.div>
            ))}
            <div ref={sentinelRef} aria-hidden style={{ height: 1 }} />
            {isFetchingNextPage ? <Skeleton height={120} /> : null}
            {!hasNextPage && posts.length > 0 ? (
              <Typography
                level="body-xs"
                textColor="text.tertiary"
                sx={{ textAlign: "center", py: 2 }}
              >
                You&apos;re all caught up.
              </Typography>
            ) : null}
          </Stack>
        </AnimatePresence>
      )}
    </Stack>
  );
}

export default PostsTab;
