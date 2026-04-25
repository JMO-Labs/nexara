/**
 * @file tests/unit/subgroups/useSubgroups.test.tsx
 * @brief Verify list query + join mutation invalidates the list key.
 */
import * as React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { qk } from '@/lib/query-keys';
import { useToasts } from '@/stores/toasts';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      'toasts.subgroups.joined': 'Joined subgroup',
      'toasts.errors.generic': 'Something went wrong',
    };
    return translations[key] || key;
  },
}));

vi.mock('@/lib/api/subgroups', () => ({
  listSubgroups: vi.fn(),
  joinSubgroup: vi.fn(),
  leaveSubgroup: vi.fn(),
  getSubgroup: vi.fn(),
  createSubgroup: vi.fn(),
  updateSubgroup: vi.fn(),
  deleteSubgroup: vi.fn(),
  listMembers: vi.fn(),
  addMember: vi.fn(),
  changeMemberRole: vi.fn(),
  removeMember: vi.fn(),
}));

import * as api from '@/lib/api/subgroups';
import { useSubgroupList, useJoinSubgroup } from '@/hooks/useSubgroups';

function wrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe('useSubgroups', () => {
  let qc: QueryClient;
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
    qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  });

  it('useSubgroupList returns api result', async () => {
    (api.listSubgroups as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: '1', slug: 'a', name: 'A' },
    ]);
    const { result } = renderHook(() => useSubgroupList(), { wrapper: wrapper(qc) });
    await waitFor(() => expect(result.current.data?.length).toBe(1));
  });

  it('useJoinSubgroup invalidates list key', async () => {
    (api.joinSubgroup as ReturnType<typeof vi.fn>).mockResolvedValue({});
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useJoinSubgroup(), { wrapper: wrapper(qc) });
    await act(async () => {
      await result.current.mutateAsync('hiking');
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: qk.subgroups.list() });
  });
});
