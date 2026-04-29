/**
 * @file tests/unit/hooks/useHomeSummary.test.tsx
 * @brief Unit tests for useHomeSummary hook.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

import * as homeApi from '@/lib/api/home';
import { useHomeSummary } from '@/hooks/useHomeSummary';

vi.mock('@/lib/api/home');

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  Wrapper.displayName = 'Wrapper';
  return Wrapper;
}

describe('useHomeSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns summary data on success', async () => {
    vi.mocked(homeApi.getHomeSummary).mockResolvedValue({
      new_posts: 5,
      upcoming_events: 2,
      unread_notifications: 10,
    });

    const { result } = renderHook(() => useHomeSummary(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({
      new_posts: 5,
      upcoming_events: 2,
      unread_notifications: 10,
    });
  });

  it('reflects isError on failure', async () => {
    vi.mocked(homeApi.getHomeSummary).mockRejectedValue(new Error('fail'));

    const { result } = renderHook(() => useHomeSummary(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
