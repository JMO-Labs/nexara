/**
 * @file tests/unit/search/useGlobalSearch.test.tsx
 * @brief Verify useGlobalSearch hook enable/disable and param passing.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as React from 'react';
import { qk } from '@/lib/query-keys';
import type { SearchResponse } from '@/lib/api/search';

vi.mock('@/lib/api/search', () => ({
  searchAll: vi.fn(),
}));

import { searchAll } from '@/lib/api/search';
import { useGlobalSearch } from '@/hooks/useSearch';

function wrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe('useGlobalSearch', () => {
  let qc: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  it('stays disabled when query < 2 chars', () => {
    (searchAll as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    } as SearchResponse);

    const { result } = renderHook(() => useGlobalSearch('a'), {
      wrapper: wrapper(qc),
    });

    expect(result.current.isLoading).toBe(false);
    expect(searchAll).not.toHaveBeenCalled();
  });

  it('triggers searchAll with default scope when query >= 2 chars', async () => {
    (searchAll as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    } as SearchResponse);

    const { result } = renderHook(() => useGlobalSearch('hello'), {
      wrapper: wrapper(qc),
    });

    await waitFor(() => {
      expect(searchAll).toHaveBeenCalledWith('hello', {});
    });
  });

  it('passes types when scope is not "all"', async () => {
    (searchAll as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    } as SearchResponse);

    renderHook(() => useGlobalSearch('hello', 'posts'), {
      wrapper: wrapper(qc),
    });

    await waitFor(() => {
      expect(searchAll).toHaveBeenCalledWith('hello', { types: ['posts'] });
    });
  });

  it('uses correct query key', async () => {
    (searchAll as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    } as SearchResponse);

    const { result } = renderHook(() => useGlobalSearch('test', 'users'), {
      wrapper: wrapper(qc),
    });

    await waitFor(() => {
      const data = qc.getQueryData(qk.search.global('test', 'users'));
      expect(data).toBeDefined();
    });
  });

  it('returns data from query', async () => {
    const mockData: SearchResponse = {
      items: [
        {
          id: 'p1',
          type: 'posts',
          title: 'Post Title',
          snippet: 'Post snippet',
          created_at: '2026-04-25T00:00:00Z',
        },
      ],
      next_cursor: null,
      has_more: false,
    };
    (searchAll as ReturnType<typeof vi.fn>).mockResolvedValue(mockData);

    const { result } = renderHook(() => useGlobalSearch('hello'), {
      wrapper: wrapper(qc),
    });

    await waitFor(() => {
      expect(result.current.data).toEqual(mockData);
    });
  });
});
