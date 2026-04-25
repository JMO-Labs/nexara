/**
 * @file tests/unit/feed/usePosts.test.tsx
 * @brief Verify reaction optimistic update + create-post cache prepend.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as React from 'react';
import { qk } from '@/lib/query-keys';
import type { Post, ReactionResponse } from '@/lib/api/posts';
import { useToasts } from '@/stores/toasts';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      'toasts.posts.created': 'Post published',
      'toasts.posts.deleted': 'Post removed',
      'toasts.posts.reaction.added': 'Reacted',
      'toasts.comments.added': 'Comment posted',
      'toasts.errors.generic': 'Something went wrong',
    };
    return translations[key] || key;
  },
}));

vi.mock('@/lib/api/posts', () => ({
  togglePostReaction: vi.fn(),
  createPost: vi.fn(),
  listFeed: vi.fn(),
  getPost: vi.fn(),
  listComments: vi.fn(),
  createComment: vi.fn(),
  toggleCommentReaction: vi.fn(),
  updatePost: vi.fn(),
  deletePost: vi.fn(),
}));

import * as api from '@/lib/api/posts';
import { useTogglePostReaction, useCreatePost } from '@/hooks/usePosts';

function makePost(over: Partial<Post> = {}): Post {
  return {
    id: 'p1',
    content: 'hi',
    author: { id: 'u1', username: 'u', display_name: 'U', avatar_url: null },
    media: [],
    poll: null,
    reactions: [],
    comment_count: 0,
    created_at: '2026-04-25T00:00:00Z',
    updated_at: '2026-04-25T00:00:00Z',
    ...over,
  };
}

function wrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe('usePosts', () => {
  let qc: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  it('useTogglePostReaction applies optimistic add then syncs server count', async () => {
    qc.setQueryData(qk.feed.post('p1'), makePost());
    (api.togglePostReaction as ReturnType<typeof vi.fn>).mockResolvedValue({
      action: 'added',
      emoji: '👍',
      count: 5,
    } as ReactionResponse);

    const { result } = renderHook(() => useTogglePostReaction('p1'), {
      wrapper: wrapper(qc),
    });

    await act(async () => {
      await result.current.mutateAsync('👍');
    });

    // Optimistic: count 1 added
    await waitFor(() => {
      const cur = qc.getQueryData<Post>(qk.feed.post('p1'));
      expect(cur?.reactions.find((r) => r.emoji === '👍')?.reacted_by_me).toBe(true);
    });
    // Eventual: count synced to server-reported 5
    await waitFor(() => {
      const cur = qc.getQueryData<Post>(qk.feed.post('p1'));
      expect(cur?.reactions.find((r) => r.emoji === '👍')?.count).toBe(5);
    });
  });

  it('useCreatePost prepends new post to first feed page', async () => {
    qc.setQueryData(qk.feed.infinite({ limit: 20 }), {
      pages: [{ items: [makePost({ id: 'old' })], next_cursor: null, has_more: false }],
      pageParams: [null],
    });
    const created = makePost({ id: 'new' });
    (api.createPost as ReturnType<typeof vi.fn>).mockResolvedValue(created);

    const { result } = renderHook(() => useCreatePost(), { wrapper: wrapper(qc) });

    await act(async () => {
      await result.current.mutateAsync({ content: 'hi' });
    });

    const cache = qc.getQueryData<{
      pages: { items: Post[] }[];
    }>(qk.feed.infinite({ limit: 20 }));
    expect(cache?.pages[0].items[0].id).toBe('new');
    expect(cache?.pages[0].items[1].id).toBe('old');
  });
});
