/**
 * @file hooks/usePosts.ts
 * @brief TanStack Query hooks for feed/post/comments/reactions with optimistic updates.
 */
"use client";

import {
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useMutationWithToast } from "./useMutationWithToast";
import { qk } from "@/lib/query-keys";
import {
  listFeed,
  getPost,
  createPost,
  updatePost,
  deletePost,
  listComments,
  createComment,
  togglePostReaction,
  toggleCommentReaction,
  type Comment,
  type Cursor,
  type CreatePostBody,
  type ListFeedParams,
  type Post,
  type ReactionSummary,
} from "@/lib/api/posts";

export function useFeed(params?: ListFeedParams | null, limit = 20) {
  return useInfiniteQuery({
    queryKey: qk.feed.infinite({ ...params, limit }),
    queryFn: ({ pageParam }) =>
      listFeed({ ...params, cursor: pageParam as string | null, limit }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => (last.has_more ? last.next_cursor : undefined),
    staleTime: 30_000,
  });
}

export function usePost(id: string | undefined, initialData?: Post) {
  return useQuery({
    queryKey: qk.feed.post(id ?? ""),
    queryFn: () => getPost(id!),
    enabled: Boolean(id),
    initialData,
    staleTime: 15_000,
  });
}

export function useComments(postId: string | undefined, limit = 20) {
  return useInfiniteQuery({
    queryKey: qk.feed.comments(postId ?? ""),
    queryFn: ({ pageParam }) =>
      listComments(postId!, pageParam as string | null, limit),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => (last.has_more ? last.next_cursor : undefined),
    enabled: Boolean(postId),
  });
}

export function useCreatePost() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (body: CreatePostBody) => createPost(body),
    successKey: "toasts.posts.created",
    onSuccess: (post) => {
      qc.setQueriesData<
        { pages: Cursor<Post>[]; pageParams: unknown[] } | undefined
      >({ queryKey: qk.feed.all() }, (old) => {
        if (!old || !("pages" in old)) return old;
        const pages = [...old.pages];
        if (pages.length === 0) return old;
        pages[0] = { ...pages[0], items: [post, ...pages[0].items] };
        return { ...old, pages };
      });
      // Invalidate all feed queries to catch any subgroup-scoped feeds
      qc.invalidateQueries({ queryKey: qk.feed.all() });
    },
  });
}

export function useUpdatePost() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      updatePost(id, content),
    onSuccess: (post) => {
      qc.setQueryData(qk.feed.post(post.id), post);
      qc.invalidateQueries({ queryKey: qk.feed.all() });
    },
  });
}

export function useDeletePost() {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (id: string) => deletePost(id),
    successKey: "toasts.posts.deleted",
    onSuccess: (_, id) => {
      qc.setQueriesData<
        { pages: Cursor<Post>[]; pageParams: unknown[] } | undefined
      >({ queryKey: qk.feed.all() }, (old) => {
        if (!old || !("pages" in old)) return old;
        return {
          ...old,
          pages: old.pages.map((p) => ({
            ...p,
            items: p.items.filter((i) => i.id !== id),
          })),
        };
      });
      qc.removeQueries({ queryKey: qk.feed.post(id) });
    },
  });
}

export function useCreateComment(postId: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: ({
      content,
      parent_id,
    }: {
      content: string;
      parent_id?: string;
    }) => createComment(postId, content, parent_id),
    successKey: "toasts.comments.added",
    onSuccess: (comment) => {
      qc.setQueriesData<
        { pages: Cursor<Comment>[]; pageParams: unknown[] } | undefined
      >({ queryKey: qk.feed.comments(postId) }, (old) => {
        if (!old) return old;
        const pages = [...old.pages];
        if (pages.length === 0) return old;
        // append to first page (newest-first feed)
        pages[0] = { ...pages[0], items: [comment, ...pages[0].items] };
        return { ...old, pages };
      });
      qc.setQueryData<Post | undefined>(qk.feed.post(postId), (p) =>
        p ? { ...p, comment_count: p.comment_count + 1 } : p,
      );
      qc.setQueriesData<
        { pages: Cursor<Post>[]; pageParams: unknown[] } | undefined
      >({ queryKey: qk.feed.all() }, (old) => {
        if (!old || !("pages" in old)) return old;
        return {
          ...old,
          pages: old.pages.map((p) => ({
            ...p,
            items: p.items.map((i) =>
              i.id === postId
                ? { ...i, comment_count: i.comment_count + 1 }
                : i,
            ),
          })),
        };
      });
    },
  });
}

function applyReactionToList(
  reactions: ReactionSummary[],
  emoji: string,
  action: "added" | "removed",
  count: number,
): ReactionSummary[] {
  const idx = reactions.findIndex((r) => r.emoji === emoji);
  if (idx === -1) {
    if (action === "removed") return reactions;
    return [...reactions, { emoji, count, reacted_by_me: true }];
  }
  const next = [...reactions];
  next[idx] = { emoji, count, reacted_by_me: action === "added" };
  return next.filter((r) => r.count > 0);
}

export function useTogglePostReaction(postId: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: (emoji: string) => togglePostReaction(postId, emoji),
    successKey: "toasts.posts.reaction.added",
    silentSuccess: true,
    onMutate: async (emoji) => {
      // optimistic toggle
      const prevReacted = qc
        .getQueryData<Post>(qk.feed.post(postId))
        ?.reactions.find((r) => r.emoji === emoji)?.reacted_by_me;
      const optimisticAction = prevReacted ? "removed" : "added";
      const apply = (reactions: ReactionSummary[]) => {
        const existing = reactions.find((r) => r.emoji === emoji);
        const nextCount =
          (existing?.count ?? 0) + (optimisticAction === "added" ? 1 : -1);
        return applyReactionToList(
          reactions,
          emoji,
          optimisticAction,
          Math.max(0, nextCount),
        );
      };
      qc.setQueryData<Post | undefined>(qk.feed.post(postId), (p) =>
        p ? { ...p, reactions: apply(p.reactions) } : p,
      );
      qc.setQueriesData<
        { pages: Cursor<Post>[]; pageParams: unknown[] } | undefined
      >({ queryKey: qk.feed.all() }, (old) => {
        if (!old || !("pages" in old)) return old;
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
      return { emoji };
    },
    onSuccess: (resp) => {
      const apply = (reactions: ReactionSummary[]) =>
        applyReactionToList(reactions, resp.emoji, resp.action, resp.count);
      qc.setQueryData<Post | undefined>(qk.feed.post(postId), (p) =>
        p ? { ...p, reactions: apply(p.reactions) } : p,
      );
      qc.setQueriesData<
        { pages: Cursor<Post>[]; pageParams: unknown[] } | undefined
      >({ queryKey: qk.feed.all() }, (old) => {
        if (!old || !("pages" in old)) return old;
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
    },
    onError: () => {
      qc.invalidateQueries({ queryKey: qk.feed.post(postId) });
      qc.invalidateQueries({ queryKey: qk.feed.all() });
    },
  });
}

export function useToggleCommentReaction(postId: string) {
  const qc = useQueryClient();
  return useMutationWithToast({
    mutationFn: ({ commentId, emoji }: { commentId: string; emoji: string }) =>
      toggleCommentReaction(postId, commentId, emoji),
    successKey: "toasts.posts.reaction.added",
    silentSuccess: true,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.feed.comments(postId) });
    },
  });
}
