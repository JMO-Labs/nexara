'use client';
/**
 * @file components/feed/CommentThread.tsx
 * @brief Threaded comments list with a single inline reply input.
 */
import * as React from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Box from '@mui/joy/Box';
import { formatDistanceToNowStrict } from 'date-fns';
import { Avatar, Button, Textarea, Skeleton, Markdown } from '@/components/ui';
import { useComments, useCreateComment } from '@/hooks/usePosts';
import type { Comment } from '@/lib/api/posts';

const COLLAPSED_MAX = 280;
const EXPANDED_MAX = 600;

interface CommentNodeProps {
  comment: Comment;
  depth?: number;
  onReply: (parentId: string) => void;
}

function CommentNode({ comment, depth = 0, onReply }: CommentNodeProps) {
  const time = React.useMemo(() => {
    try {
      return formatDistanceToNowStrict(new Date(comment.created_at), { addSuffix: true });
    } catch {
      return '';
    }
  }, [comment.created_at]);
  return (
    <Stack
      direction="row"
      spacing={1.25}
      sx={{ pl: Math.min(depth, 3) * 3, mt: 1 }}
    >
      <Avatar src={comment.author.avatar_url ?? undefined} size="sm">
        {comment.author.display_name.charAt(0)}
      </Avatar>
      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Box
          sx={{
            backgroundColor: 'background.level1',
            borderRadius: 'md',
            px: 1.5,
            py: 1,
          }}
        >
          <Typography level="title-sm">{comment.author.display_name}</Typography>
          <Markdown content={comment.content} size="sm" />
        </Box>
        <Stack direction="row" spacing={1.5} sx={{ mt: 0.5, ml: 1 }} alignItems="center">
          <Typography level="body-xs" textColor="text.tertiary">
            {time}
          </Typography>
          <Typography
            level="body-xs"
            sx={{ cursor: 'pointer' }}
            onClick={() => onReply(comment.id)}
          >
            Reply
          </Typography>
        </Stack>
        {comment.replies?.map((r) => (
          <CommentNode key={r.id} comment={r} depth={depth + 1} onReply={onReply} />
        ))}
      </Box>
    </Stack>
  );
}

export interface CommentThreadProps {
  postId: string;
  expanded?: boolean;
  onOverflowChange?: (overflowing: boolean) => void;
}

export function CommentThread({ postId, expanded = false, onOverflowChange }: CommentThreadProps) {
  const { data, isLoading, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useComments(postId);
  const createMut = useCreateComment(postId);
  const [text, setText] = React.useState('');
  const [replyTo, setReplyTo] = React.useState<string | null>(null);
  const scrollRef = React.useRef<HTMLDivElement | null>(null);

  const flat = React.useMemo(
    () => (data?.pages ?? []).flatMap((p) => p.items),
    [data],
  );

  React.useEffect(() => {
    const el = scrollRef.current;
    if (!el || !onOverflowChange) return;
    onOverflowChange(el.scrollHeight > el.clientHeight + 4);
  }, [flat, expanded, onOverflowChange]);

  const submit = async () => {
    const content = text.trim();
    if (!content) return;
    try {
      await createMut.mutateAsync({
        content,
        parent_id: replyTo ?? undefined,
      });
      setText('');
      setReplyTo(null);
    } catch {
      /* surface via toast in caller */
    }
  };

  return (
    <Stack spacing={1} sx={{ mt: 1 }}>
      <Stack direction="row" spacing={1} alignItems="flex-start">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={replyTo ? 'Write a reply…' : 'Add a comment…'}
          minRows={1}
          maxRows={6}
          sx={{ flexGrow: 1 }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <Button
          size="sm"
          onClick={submit}
          loading={createMut.isPending}
          disabled={!text.trim()}
        >
          Send
        </Button>
      </Stack>
      {replyTo ? (
        <Typography level="body-xs" sx={{ cursor: 'pointer' }} onClick={() => setReplyTo(null)}>
          Cancel reply
        </Typography>
      ) : null}
      {isLoading ? (
        <Stack spacing={1}>
          <Skeleton height={48} />
          <Skeleton height={48} />
        </Stack>
      ) : flat.length === 0 ? (
        <Typography level="body-sm" textColor="text.tertiary" sx={{ py: 1 }}>
          No comments yet.
        </Typography>
      ) : (
        <Box
          ref={scrollRef}
          sx={{
            maxHeight: expanded ? EXPANDED_MAX : COLLAPSED_MAX,
            overflowY: 'auto',
            pr: 0.5,
            transition: 'max-height 200ms ease',
            borderTop: '1px solid',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          {flat.map((c) => (
            <CommentNode key={c.id} comment={c} onReply={setReplyTo} />
          ))}
          {hasNextPage ? (
            <Button
              variant="plain"
              size="sm"
              onClick={() => fetchNextPage()}
              loading={isFetchingNextPage}
              sx={{ mt: 1 }}
            >
              Load more
            </Button>
          ) : null}
        </Box>
      )}
    </Stack>
  );
}

export default CommentThread;
