'use client';
/**
 * @file components/feed/FeedView.tsx
 * @brief Reusable feed (composer + infinite list). Shared by /app dashboard.
 */
import * as React from 'react';
import { useRouter } from 'next/navigation';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { Button, EmptyState, Skeleton } from '@/components/ui';
import { PostCard } from './PostCard';
import { PostComposer } from './PostComposer';
import { useFeed } from '@/hooks/usePosts';
import { useFeedRealtime } from '@/hooks/useFeedRealtime';

export interface FeedViewProps {
  heading?: React.ReactNode;
}

export function FeedView({ heading }: FeedViewProps) {
  const {
    data,
    isLoading,
    isError,
    error,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    refetch,
  } = useFeed();
  useFeedRealtime();
  const router = useRouter();

  const sentinelRef = React.useRef<HTMLDivElement | null>(null);
  React.useEffect(() => {
    const el = sentinelRef.current;
    if (!el || !hasNextPage) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isFetchingNextPage) fetchNextPage();
      },
      { rootMargin: '300px' },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  const posts = React.useMemo(
    () => (data?.pages ?? []).flatMap((p) => p.items),
    [data],
  );

  return (
    <Stack spacing={2} sx={{ width: '100%' }}>
      {heading}
      <PostComposer />
      {isLoading ? (
        <Stack spacing={2}>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} height={180} />
          ))}
        </Stack>
      ) : isError ? (
        <EmptyState
          title="Couldn’t load the feed"
          description={error instanceof Error ? error.message : 'Try again in a moment.'}
          action={<Button onClick={() => refetch()}>Retry</Button>}
        />
      ) : posts.length === 0 ? (
        <EmptyState
          title="It’s quiet here"
          description="Be the first to share something with your community."
        />
      ) : (
        <Stack spacing={2}>
          {posts.map((p) => (
            <PostCard
              key={p.id}
              post={p}
              truncateBody
              onOpen={(id) => router.push(`/app/post/${id}`)}
            />
          ))}
          <div ref={sentinelRef} aria-hidden style={{ height: 1 }} />
          {isFetchingNextPage ? <Skeleton height={120} /> : null}
          {!hasNextPage && posts.length > 0 ? (
            <Typography
              level="body-xs"
              textColor="text.tertiary"
              sx={{ textAlign: 'center', py: 2 }}
            >
              You’re all caught up.
            </Typography>
          ) : null}
        </Stack>
      )}
    </Stack>
  );
}

export default FeedView;
