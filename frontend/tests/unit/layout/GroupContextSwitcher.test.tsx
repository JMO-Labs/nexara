/**
 * @file tests/unit/layout/GroupContextSwitcher.test.tsx
 * @brief GroupContextSwitcher visibility and navigation tests.
 */
import * as React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CssVarsProvider } from '@mui/joy/styles';
import joyTheme from '@/theme/joy-theme';
import { GroupContextSwitcher } from '@/components/layout/GroupContextSwitcher';
import * as useSubgroupsModule from '@/hooks/useSubgroups';
import type { Subgroup } from '@/lib/api/subgroups';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  usePathname: vi.fn(),
}));

import { usePathname } from 'next/navigation';

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

const subgroupA: Subgroup = {
  id: 'sg1',
  name: 'Hiking Club',
  slug: 'hiking-club',
  description: 'Trail adventures',
  avatar_url: null,
  cover_media_id: null,
  is_private: false,
  join_policy: 'open',
  created_by: null,
  parent_id: null,
  archived_at: null,
  created_at: '2026-04-25T00:00:00Z',
  updated_at: '2026-04-25T00:00:00Z',
};

const subgroupB: Subgroup = {
  id: 'sg2',
  name: 'Tech Board',
  slug: 'tech-board',
  description: 'Tech talk',
  avatar_url: null,
  cover_media_id: null,
  is_private: false,
  join_policy: 'open',
  created_by: null,
  parent_id: null,
  archived_at: null,
  created_at: '2026-04-25T00:00:00Z',
  updated_at: '2026-04-25T00:00:00Z',
};

describe('GroupContextSwitcher', () => {
  beforeEach(() => {
    vi.mocked(usePathname).mockReturnValue('/app/dashboard');
  });

  it('renders nothing when list is empty', () => {
    vi.spyOn(useSubgroupsModule, 'useSubgroupList').mockReturnValue({
      data: [],
      isPending: false,
      isLoading: false,
      error: null,
      status: 'success',
    } as any);

    const { container } = wrap(<GroupContextSwitcher />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when user has 1 group and not on group route', () => {
    vi.spyOn(useSubgroupsModule, 'useSubgroupList').mockReturnValue({
      data: [subgroupA],
      isPending: false,
      isLoading: false,
      error: null,
      status: 'success',
    } as any);

    const { container } = wrap(<GroupContextSwitcher />);
    expect(container.firstChild).toBeNull();
  });

  it('renders "Groups ▾" when user has 2+ groups and not on group route', () => {
    vi.spyOn(useSubgroupsModule, 'useSubgroupList').mockReturnValue({
      data: [subgroupA, subgroupB],
      isPending: false,
      isLoading: false,
      error: null,
      status: 'success',
    } as any);

    wrap(<GroupContextSwitcher />);
    expect(screen.getByText(/Groups ▾/)).toBeInTheDocument();
  });

  it('renders active group name when path matches /app/subgroups/<slug>', () => {
    vi.mocked(usePathname).mockReturnValue('/app/subgroups/hiking-club');
    vi.spyOn(useSubgroupsModule, 'useSubgroupList').mockReturnValue({
      data: [subgroupA, subgroupB],
      isPending: false,
      isLoading: false,
      error: null,
      status: 'success',
    } as any);

    wrap(<GroupContextSwitcher />);
    expect(screen.getByText(/Hiking Club ▾/)).toBeInTheDocument();
  });

  it('opens menu when button clicked', async () => {
    vi.spyOn(useSubgroupsModule, 'useSubgroupList').mockReturnValue({
      data: [subgroupA, subgroupB],
      isPending: false,
      isLoading: false,
      error: null,
      status: 'success',
    } as any);

    wrap(<GroupContextSwitcher />);
    const button = screen.getByRole('button', { name: 'Switch group context' });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('Hiking Club')).toBeInTheDocument();
      expect(screen.getByText('Tech Board')).toBeInTheDocument();
    });
  });
});
