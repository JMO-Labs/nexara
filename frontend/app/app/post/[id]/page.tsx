'use client';
/**
 * @file app/app/post/[id]/page.tsx
 * @brief Full-screen post detail (mobile + direct/refresh navigation).
 */
import { use } from 'react';
import Stack from '@mui/joy/Stack';
import Box from '@mui/joy/Box';
import { EmptyState, Skeleton } from '@/components/ui';
import { PostCard } from '@/components/feed/PostCard';
import { CommentThread } from '@/components/feed/CommentThread';
import { usePost } from '@/hooks/usePosts';
import JoyButton from '@mui/joy/Button';
import Link from 'next/link';

export default function PostPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: post, isLoading, isError } = usePost(id);

  return (
    <Stack spacing={2} sx={{ width: '100%', maxWidth: 720, mx: 'auto' }}>
      <Box>
        <JoyButton component={Link} href="/app" variant="plain" size="sm">
          ← Back
        </JoyButton>
      </Box>
      {isLoading ? (
        <Skeleton height={240} />
      ) : isError || !post ? (
        <EmptyState title="Post not found" description="It may have been deleted." />
      ) : (
        <Stack spacing={2}>
          <PostCard post={post} />
          <CommentThread postId={post.id} />
        </Stack>
      )}
    </Stack>
  );
}
