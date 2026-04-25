'use client';
/**
 * @file hooks/useFeedRealtime.ts
 * @brief Subscribes to SSE feed_update events and updates React Query cache
 *        in place — new posts prepend, comments bump count, reactions sync.
 */
import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE } from './useSSE';
import { qk } from '@/lib/query-keys';
import { STREAM_PATH } from '@/lib/api/notifications';
import type { Comment, Cursor, Post, ReactionSummary } from '@/lib/api/posts';

interface FeedUpdatePayload {
  event: 'created' | 'comment_created' | 'reaction_toggled' | 'poll_voted';
  post?: Post;
  post_id?: string;
  comment?: Comment;
  user_id?: string;
  target_type?: 'post' | 'comment';
  target_id?: string;
  emoji?: string;
  count?: number;
  action?: 'added' | 'removed';
}

function applyReaction(
  reactions: ReactionSummary[],
  emoji: string,
  count: number,
  reactedByMe: boolean,
): ReactionSummary[] {
  const idx = reactions.findIndex((r) => r.emoji === emoji);
  if (idx === -1) {
    if (count <= 0) return reactions;
    return [...reactions, { emoji, count, reacted_by_me: reactedByMe }];
  }
  const next = [...reactions];
  next[idx] = { emoji, count, reacted_by_me: reactedByMe };
  return next.filter((r) => r.count > 0);
}

export function useFeedRealtime() {
  const qc = useQueryClient();

  const onMessage = React.useCallback(
    (data: unknown, type: string) => {
      if (type !== 'feed_update' || !data || typeof data !== 'object') return;
      const payload = data as FeedUpdatePayload;

      if (payload.event === 'created' && payload.post) {
        const post = payload.post;
        qc.setQueriesData<
          { pages: Cursor<Post>[]; pageParams: unknown[] } | undefined
        >({ queryKey: qk.feed.all() }, (old) => {
          if (!old || !('pages' in old) || old.pages.length === 0) return old;
          if (old.pages[0].items.some((i) => i.id === post.id)) return old;
          const pages = [...old.pages];
          pages[0] = { ...pages[0], items: [post, ...pages[0].items] };
          return { ...old, pages };
        });
      } else if (
        payload.event === 'comment_created' &&
        payload.post_id &&
        payload.comment
      ) {
        const postId = payload.post_id;
        qc.setQueryData<Post | undefined>(qk.feed.post(postId), (p) =>
          p ? { ...p, comment_count: p.comment_count + 1 } : p,
        );
        qc.setQueriesData<
          { pages: Cursor<Post>[]; pageParams: unknown[] } | undefined
        >({ queryKey: qk.feed.all() }, (old) => {
          if (!old || !('pages' in old)) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              items: page.items.map((i) =>
                i.id === postId ? { ...i, comment_count: i.comment_count + 1 } : i,
              ),
            })),
          };
        });
        qc.invalidateQueries({ queryKey: qk.feed.comments(postId) });
      } else if (
        payload.event === 'reaction_toggled' &&
        payload.target_type === 'post' &&
        payload.post_id &&
        payload.emoji &&
        typeof payload.count === 'number'
      ) {
        const postId = payload.post_id;
        const emoji = payload.emoji;
        const count = payload.count;
        const apply = (reactions: ReactionSummary[]) =>
          applyReaction(
            reactions,
            emoji,
            count,
            reactions.find((r) => r.emoji === emoji)?.reacted_by_me ?? false,
          );
        qc.setQueryData<Post | undefined>(qk.feed.post(postId), (p) =>
          p ? { ...p, reactions: apply(p.reactions) } : p,
        );
        qc.setQueriesData<
          { pages: Cursor<Post>[]; pageParams: unknown[] } | undefined
        >({ queryKey: qk.feed.all() }, (old) => {
          if (!old || !('pages' in old)) return old;
          return {
            ...old,
            pages: old.pages.map((page) => ({
              ...page,
              items: page.items.map((i) =>
                i.id === postId ? { ...i, reactions: apply(i.reactions) } : i,
              ),
            })),
          };
        });
      }
    },
    [qc],
  );

  useSSE(STREAM_PATH, {
    onMessage,
    eventTypes: ['feed_update'],
  });
}
