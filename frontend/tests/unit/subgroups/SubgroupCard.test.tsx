/**
 * @file tests/unit/subgroups/SubgroupCard.test.tsx
 * @brief Renders subgroup card; join/leave/select callbacks fire correctly.
 */
import * as React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CssVarsProvider } from '@mui/joy/styles';
import joyTheme from '@/theme/joy-theme';
import { SubgroupCard } from '@/components/subgroups/SubgroupCard';
import type { Subgroup } from '@/lib/api/subgroups';

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

const sg: Subgroup = {
  id: 'sg1',
  name: 'Hiking',
  slug: 'hiking',
  description: 'Trails',
  avatar_url: null,
  is_private: false,
  join_policy: 'open',
  created_by: null,
  parent_id: null,
  archived_at: null,
  created_at: '2026-04-25T00:00:00Z',
  updated_at: '2026-04-25T00:00:00Z',
};

describe('SubgroupCard', () => {
  it('renders name + description + member count', () => {
    wrap(<SubgroupCard subgroup={sg} memberCount={4} onSelect={() => {}} />);
    expect(screen.getByText('Hiking')).toBeInTheDocument();
    expect(screen.getByText('Trails')).toBeInTheDocument();
    expect(screen.getByText(/4 members/)).toBeInTheDocument();
  });

  it('fires onJoin when not a member', () => {
    const onJoin = vi.fn();
    wrap(<SubgroupCard subgroup={sg} onSelect={() => {}} onJoin={onJoin} />);
    fireEvent.click(screen.getByRole('button', { name: 'Join' }));
    expect(onJoin).toHaveBeenCalledWith('hiking');
  });

  it('fires onLeave when member', () => {
    const onLeave = vi.fn();
    wrap(<SubgroupCard subgroup={sg} isMember onSelect={() => {}} onLeave={onLeave} />);
    fireEvent.click(screen.getByRole('button', { name: 'Leave' }));
    expect(onLeave).toHaveBeenCalledWith('hiking');
  });
});
