"use client";
/**
 * @file components/feed/PostCard.tsx
 * @brief Composes Header/Body/Media/ReactionRow into a feed card.
 *        Comment thread rendered conditionally when expanded.
 */
import * as React from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button, Card } from "@/components/ui";
import { useSession } from "@/stores/session";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useDeletePost, useTogglePostReaction } from "@/hooks/usePosts";
import { PostHeader } from "./PostHeader";
import { PostBody } from "./PostBody";
import { PostMedia } from "./PostMedia";
import { ReactionRow } from "./ReactionRow";
import { CommentThread } from "./CommentThread";
import { LinkPreviewCard } from "@/components/content/LinkPreviewCard";
import { VideoEmbed, embedUrl } from "@/components/content/VideoEmbed";
import { SourceBadge } from "./SourceBadge";
import { KudosCard } from "./KudosCard";
import { PromptBadges } from "./PromptBadges";
import type { Post } from "@/lib/api/posts";

export interface PostCardProps {
  post: Post;
  onOpen?: (id: string) => void;
  defaultCommentsOpen?: boolean;
  truncateBody?: boolean;
}

/**
 * @brief Feed card for a single post.
 * @param post the post
 * @param onOpen open-detail callback (media click)
 * @param defaultCommentsOpen start with comments expanded
 * @param truncateBody clamp long bodies
 * @return card element
 */
export function PostCard({
  post,
  onOpen,
  defaultCommentsOpen = false,
  truncateBody = false,
}: PostCardProps) {
  const me = useSession((s) => s.user);
  const isAuthor = me?.id === post.author.id;
  const isAdmin = me?.role === "admin" || me?.role === "owner";
  const [commentsOpen, setCommentsOpen] = React.useState(defaultCommentsOpen);
  const [commentsExpanded, setCommentsExpanded] = React.useState(false);
  const [commentsOverflowing, setCommentsOverflowing] = React.useState(false);
  const reactMut = useTogglePostReaction(post.id);
  const delMut = useDeletePost();
  const confirm = useConfirmDialog((s) => s.confirm);

  if (post.recipient_id && post.recipient) {
    return (
      <KudosCard
        recipient={post.recipient}
        message={post.content}
        authorName={post.author.display_name}
        createdAt={post.created_at}
      />
    );
  }

  const headline = post.content.split("\n")[0].trim().slice(0, 80);
  const reactionTotal = post.reactions.reduce((n, r) => n + r.count, 0);
  const cardLabel = `Post by ${post.author.display_name}${headline ? `: ${headline}` : ""}. ${reactionTotal} ${reactionTotal === 1 ? "reaction" : "reactions"}, ${post.comment_count} ${post.comment_count === 1 ? "comment" : "comments"}.`;

  return (
    <Card
      role="article"
      aria-label={cardLabel}
      className="flex flex-col gap-3 p-3 transition-colors hover:bg-[color-mix(in_srgb,var(--nx-ink)_4%,var(--nx-surface))] md:p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <PostHeader
          post={post}
          isAuthor={isAuthor}
          isAdmin={isAdmin}
          onDelete={async () => {
            const ok = await confirm({
              title: "Delete post?",
              message: "This post will be permanently deleted.",
              confirmLabel: "Delete",
              tone: "danger",
            });
            if (ok) delMut.mutate(post.id);
          }}
        />
        <SourceBadge
          subgroupId={post.subgroup_id ?? null}
          subgroupName={post.subgroup_name ?? null}
          subgroupSlug={post.subgroup_slug ?? null}
        />
      </div>
      <PromptBadges
        isPromptSummary={post.is_prompt_summary}
        replyToPromptId={post.reply_to_prompt_id}
      />
      <PostBody content={post.content} truncate={truncateBody} />
      {post.link_previews && post.link_previews.length > 0 ? (
        <div
          data-testid="post-previews"
          className="mt-3 min-w-0 max-w-full space-y-2"
        >
          {post.link_previews.map((preview) =>
            preview.provider_type && embedUrl(preview) ? (
              <VideoEmbed key={preview.id} preview={preview} />
            ) : (
              <LinkPreviewCard key={preview.id} preview={preview} />
            ),
          )}
        </div>
      ) : null}
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
      {commentsOpen &&
      post.comment_count > 0 &&
      (commentsOverflowing || commentsExpanded) ? (
        <Button
          variant="ghost"
          size="sm"
          className="self-start"
          aria-expanded={commentsExpanded}
          onClick={() => setCommentsExpanded((v) => !v)}
        >
          {commentsExpanded ? (
            <ChevronUp className="size-4" aria-hidden="true" />
          ) : (
            <ChevronDown className="size-4" aria-hidden="true" />
          )}
          {commentsExpanded ? "Collapse comments" : "Expand comments"}
        </Button>
      ) : null}
    </Card>
  );
}

export default PostCard;
