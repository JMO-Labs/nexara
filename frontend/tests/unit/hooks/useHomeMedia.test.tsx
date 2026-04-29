/**
 * @file tests/unit/hooks/useHomeMedia.test.tsx
 * @brief Unit tests for useHomeMedia hook.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

import * as homeApi from '@/lib/api/home';
import { useHomeMedia } from '@/hooks/useHomeMedia';
import type { HomeMediaItem } from '@/lib/api/home';

vi.mock('@/lib/api/home');

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  Wrapper.displayName = 'Wrapper';
  return Wrapper;
}

const MOCK_ITEM: HomeMediaItem = {
  media_id: 'mid-1',
  media: {
    id: 'mid-1',
    filename: 'photo.jpg',
    content_type: 'image/jpeg',
    storage_key: 'key/photo.jpg',
    thumbnail_key: null,
    size_bytes: 1024,
    width: 800,
    height: 600,
    duration_secs: null,
    alt_text: null,
    status: 'ready',
    created_at: '2026-04-28T10:00:00Z',
  },
  source: 'post',
  source_id: 'src-1',
  source_title: 'A post',
  created_at: '2026-04-28T10:00:00Z',
};

describe('useHomeMedia', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns media items on success', async () => {
    vi.mocked(homeApi.getHomeMedia).mockResolvedValue({
      items: [MOCK_ITEM],
      next_cursor: null,
    });

    const { result } = renderHook(() => useHomeMedia(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0].media_id).toBe('mid-1');
  });

  it('passes custom limit to the API call', async () => {
    vi.mocked(homeApi.getHomeMedia).mockResolvedValue({ items: [], next_cursor: null });

    const { result } = renderHook(() => useHomeMedia(12), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(homeApi.getHomeMedia).toHaveBeenCalledWith(12);
  });

  it('uses default limit 24 when none provided', async () => {
    vi.mocked(homeApi.getHomeMedia).mockResolvedValue({ items: [], next_cursor: null });

    const { result } = renderHook(() => useHomeMedia(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(homeApi.getHomeMedia).toHaveBeenCalledWith(24);
  });

  it('reflects isError on failure', async () => {
    vi.mocked(homeApi.getHomeMedia).mockRejectedValue(new Error('fail'));

    const { result } = renderHook(() => useHomeMedia(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
