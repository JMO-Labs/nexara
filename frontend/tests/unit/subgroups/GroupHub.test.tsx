/**
 * @file tests/unit/subgroups/GroupHub.test.tsx
 * @brief Group hub page: masthead renders, tab URL sync, member-only gate.
 */
import * as React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CssVarsProvider } from '@mui/joy/styles';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import joyTheme from '@/theme/joy-theme';
import { GroupHub } from '@/components/subgroups/hub/GroupHub';
import * as useSubgroupsModule from '@/hooks/useSubgroups';
import type { SubgroupDetail } from '@/lib/api/subgroups';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    replace: vi.fn(),
    push: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockSubgroupDetail: SubgroupDetail = {
  id: 'sg1',
  name: 'Hiking Club',
  slug: 'hiking',
  description: 'Outdoor enthusiasts',
  avatar_url: null,
  cover_media_id: null,
  is_private: false,
  join_policy: 'open',
  created_by: null,
  parent_id: null,
  archived_at: null,
  created_at: '2026-04-25T00:00:00Z',
  updated_at: '2026-04-25T00:00:00Z',
  member_count: 12,
  my_role: 'member',
  chat_channel_id: null,
  pinned_post_id: null,
};

const mockInviteOnlySubgroup: SubgroupDetail = {
  ...mockSubgroupDetail,
  join_policy: 'invite_only',
  my_role: null,
};

function wrap(ui: React.ReactNode, queryClient?: QueryClient) {
  const qc = queryClient || new QueryClient();
  return render(
    <NextIntlClientProvider locale="en" messages={{}}>
      <QueryClientProvider client={qc}>
        <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

describe('GroupHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton when data is loading', () => {
    vi.spyOn(useSubgroupsModule, 'useSubgroupDetail').mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
      isFetching: false,
      isPending: true,
      isSuccess: false,
      status: 'pending',
    } as any);

    wrap(<GroupHub slug="hiking" />);
    expect(screen.getAllByRole('status')).toHaveLength(2);
  });

  it('renders title on cover band (not duplicated below)', () => {
    vi.spyOn(useSubgroupsModule, 'useSubgroupDetail').mockReturnValue({
      data: mockSubgroupDetail,
      isLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      isPending: false,
      isSuccess: true,
      status: 'success',
    } as any);

    wrap(<GroupHub slug="hiking" />);
    const titleElements = screen.getAllByText('Hiking Club');
    // Should appear only once (on cover overlay)
    expect(titleElements).toHaveLength(1);
    expect(screen.getByText(/12 members.*public/i)).toBeInTheDocument();
  });

  it('renders vertical tab nav when member', () => {
    vi.spyOn(useSubgroupsModule, 'useSubgroupDetail').mockReturnValue({
      data: mockSubgroupDetail,
      isLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      isPending: false,
      isSuccess: true,
      status: 'success',
    } as any);

    wrap(<GroupHub slug="hiking" />);

    // Members nav button(s) visible (desktop list + mobile strip both rendered in jsdom)
    expect(screen.getAllByRole('button', { name: /members/i }).length).toBeGreaterThan(0);
    // Settings hidden for member role
    expect(screen.queryAllByRole('button', { name: /settings/i }).length).toBe(0);
  });

  it('shows Settings tab for owner', () => {
    const ownerSubgroup: SubgroupDetail = {
      ...mockSubgroupDetail,
      my_role: 'owner',
    };
    vi.spyOn(useSubgroupsModule, 'useSubgroupDetail').mockReturnValue({
      data: ownerSubgroup,
      isLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      isPending: false,
      isSuccess: true,
      status: 'success',
    } as any);

    wrap(<GroupHub slug="hiking" />);

    expect(screen.getAllByRole('button', { name: /settings/i }).length).toBeGreaterThan(0);
  });

  it('shows MemberOnlyGate when user is not member of invite_only group', () => {
    vi.spyOn(useSubgroupsModule, 'useSubgroupDetail').mockReturnValue({
      data: mockInviteOnlySubgroup,
      isLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      isPending: false,
      isSuccess: true,
      status: 'success',
    } as any);

    wrap(<GroupHub slug="hiking" />);
    expect(screen.getByText(/invite required/i)).toBeInTheDocument();
    expect(screen.queryAllByRole('button', { name: /members/i }).length).toBe(0);
  });
});
