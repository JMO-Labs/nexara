"use client";
/**
 * @file components/feed/CommentThread.tsx
 * @brief Threaded comments list with a single inline reply input.
 */
import * as React from "react";
import { MentionMenu } from "@/components/mentions/MentionMenu";
import { useMentionInput } from "@/components/mentions/useMentionInput";
import { formatDistanceToNowStrict } from "date-fns";
import { MessageCircle } from "lucide-react";
import {
  Avatar,
  Button,
  EmptyState,
  Skeleton,
  Markdown,
} from "@/components/ui";
import { useComments, useCreateComment } from "@/hooks/usePosts";
import { ReportButton } from "@/components/common/ReportButton";
import type { Comment } from "@/lib/api/posts";

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
      return formatDistanceToNowStrict(new Date(comment.created_at), {
        addSuffix: true,
      });
    } catch {
      return "";
    }
  }, [comment.created_at]);
  return (
    <div
      className="mt-2 flex gap-2.5"
      style={{ paddingLeft: Math.min(depth, 3) * 12 }}
    >
      <Avatar
        src={comment.author.avatar_url ?? undefined}
        name={comment.author.display_name}
        size="sm"
        userId={comment.author.id}
      />
      <div className="min-w-0 grow">
        <div className="glass-item rounded-[20px] px-3 py-2">
          <p className="text-sm font-semibold">{comment.author.display_name}</p>
          <Markdown content={comment.content} size="sm" mentions />
        </div>
        <div className="ml-2 mt-1 flex items-center gap-3 text-xs text-ink/75">
          <span>{time}</span>
          <button
            type="button"
            onClick={() => onReply(comment.id)}
            className="rounded font-semibold outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Reply
          </button>
          <ReportButton targetType="comment" targetId={comment.id} />
        </div>
        {comment.replies?.map((r) => (
          <CommentNode
            key={r.id}
            comment={r}
            depth={depth + 1}
            onReply={onReply}
          />
        ))}
      </div>
    </div>
  );
}

export interface CommentThreadProps {
  postId: string;
  expanded?: boolean;
  onOverflowChange?: (overflowing: boolean) => void;
}

/**
 * @brief Comment list + composer for a post.
 * @param postId post id
 * @param expanded taller scroll area
 * @param onOverflowChange reports whether the list overflows its box
 * @return thread element
 */
export function CommentThread({
  postId,
  expanded = false,
  onOverflowChange,
}: CommentThreadProps) {
  const {
    data,
    isLoading,
    isError,
    refetch,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useComments(postId);
  const createMut = useCreateComment(postId);
  const [text, setText] = React.useState("");
  const [replyTo, setReplyTo] = React.useState<string | null>(null);
  const scrollRef = React.useRef<HTMLDivElement | null>(null);
  const inputRef = React.useRef<HTMLTextAreaElement | null>(null);
  const mention = useMentionInput(text, setText, inputRef);

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
      setText("");
      setReplyTo(null);
    } catch {
      /* surface via toast in caller */
    }
  };

  return (
    <div className="mt-2 flex flex-col gap-2">
      <div className="relative flex items-center gap-2 rounded-full glass-item p-1.5 pl-4">
        {mention.open && (
          <MentionMenu
            {...mention.menu}
            className="absolute bottom-full left-2 mb-2"
          />
        )}
        <textarea
          ref={inputRef}
          aria-label={replyTo ? "Write a reply" : "Add a comment"}
          aria-autocomplete="list"
          value={text}
          onChange={mention.onTextChange}
          {...mention.fieldProps}
          placeholder={replyTo ? "Write a reply…" : "Add a comment…"}
          rows={1}
          className="field-sizing-content max-h-32 grow resize-none bg-transparent py-2 text-base text-ink placeholder:text-muted outline-none"
          onKeyDown={(e) => {
            if (mention.onKeyDown(e)) return;
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
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
          className="disabled:opacity-40"
        >
          Send
        </Button>
      </div>
      {replyTo ? (
        <button
          type="button"
          onClick={() => setReplyTo(null)}
          className="self-start rounded text-xs font-semibold outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Cancel reply
        </button>
      ) : null}
      {isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton height={48} />
          <Skeleton height={48} />
        </div>
      ) : isError && flat.length === 0 ? (
        <div role="alert" className="flex items-center gap-3 py-2 text-sm">
          <span>Couldn&apos;t load comments.</span>
          <Button variant="secondary" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      ) : flat.length === 0 ? (
        <EmptyState
          compact
          icon={MessageCircle}
          title="No comments yet"
          description="Start the conversation."
        />
      ) : (
        <div
          ref={scrollRef}
          className="overflow-y-auto py-1 pr-1 motion-safe:transition-[max-height]"
          style={{ maxHeight: expanded ? EXPANDED_MAX : COLLAPSED_MAX }}
        >
          {flat.map((c) => (
            <CommentNode key={c.id} comment={c} onReply={setReplyTo} />
          ))}
          {hasNextPage ? (
            <Button
              variant="ghost"
              size="sm"
              className="mt-2"
              onClick={() => fetchNextPage()}
              loading={isFetchingNextPage}
            >
              Load more
            </Button>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default CommentThread;
