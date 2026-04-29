'use client';
/**
 * @file components/feed/PostCard.tsx
 * @brief Composes Header/Body/Media/ReactionRow into a feed card.
 *        Comment thread rendered conditionally when expanded.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import { Button, Card } from '@/components/ui';
import { useSession } from '@/stores/session';
import {
  useDeletePost,
  useTogglePostReaction,
} from '@/hooks/usePosts';
import { PostHeader } from './PostHeader';
import { PostBody } from './PostBody';
import { PostMedia } from './PostMedia';
import { ReactionRow } from './ReactionRow';
import { CommentThread } from './CommentThread';
import { SourceBadge } from './SourceBadge';
import type { Post } from '@/lib/api/posts';

export interface PostCardProps {
  post: Post;
  onOpen?: (id: string) => void;
  defaultCommentsOpen?: boolean;
  truncateBody?: boolean;
}

export function PostCard({
  post,
  onOpen,
  defaultCommentsOpen = false,
  truncateBody = false,
}: PostCardProps) {
  const me = useSession((s) => s.user);
  const isAuthor = me?.id === post.author.id;
  const isAdmin = me?.role === 'admin' || me?.role === 'owner';
  const [commentsOpen, setCommentsOpen] = React.useState(defaultCommentsOpen);
  const [commentsExpanded, setCommentsExpanded] = React.useState(false);
  const [commentsOverflowing, setCommentsOverflowing] = React.useState(false);
  const reactMut = useTogglePostReaction(post.id);
  const delMut = useDeletePost();

  return (
    <Card sx={{ p: 2 }}>
      <Stack spacing={1.5}>
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <PostHeader
            post={post}
            isAuthor={isAuthor}
            isAdmin={isAdmin}
            onDelete={() => {
              if (window.confirm('Delete this post?')) delMut.mutate(post.id);
            }}
          />
          <SourceBadge
            subgroupId={post.subgroup_id ?? null}
            subgroupName={post.subgroup_name ?? null}
          />
        </div>
        <PostBody content={post.content} truncate={truncateBody} />
        {post.media.length > 0 ? (
          <PostMedia media={post.media} onClick={() => onOpen?.(post.id)} />
        ) : null}
        <ReactionRow
          reactions={post.reactions}
          commentCount={post.comment_count}
          onReact={(e) => reactMut.mutate(e)}
          onCommentClick={() => setCommentsOpen((v) => !v)}
        />
        {commentsOpen ? (
          <CommentThread
            postId={post.id}
            expanded={commentsExpanded}
            onOverflowChange={setCommentsOverflowing}
          />
        ) : null}
        {commentsOpen && post.comment_count > 0 && (commentsOverflowing || commentsExpanded) ? (
          <Button
            variant="plain"
            size="sm"
            onClick={() => setCommentsExpanded((v) => !v)}
            startDecorator={
              commentsExpanded ? <ChevronUpIcon width={14} /> : <ChevronDownIcon width={14} />
            }
            sx={{ alignSelf: 'flex-start' }}
          >
            {commentsExpanded ? 'Collapse comments' : 'Expand comments'}
          </Button>
        ) : null}
      </Stack>
    </Card>
  );
}

export default PostCard;
