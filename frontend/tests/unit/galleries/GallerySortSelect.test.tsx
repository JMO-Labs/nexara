/**
 * @file tests/unit/galleries/GallerySortSelect.test.tsx
 * @brief Sort pill row changes sort order and fires callback.
 */
import * as React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CssVarsProvider } from '@mui/joy/styles';
import joyTheme from '@/theme/joy-theme';
import { GallerySortSelect } from '@/components/galleries/GallerySortSelect';

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe('GallerySortSelect', () => {
  it('renders three sort options', () => {
    wrap(<GallerySortSelect sort="recent" onSortChange={() => {}} />);
    expect(screen.getByRole('button', { name: 'Recent' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Popular' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Oldest' })).toBeInTheDocument();
  });

  it('highlights active sort option', () => {
    wrap(<GallerySortSelect sort="recent" onSortChange={() => {}} />);
    const recentBtn = screen.getByRole('button', { name: 'Recent' });
    expect(recentBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('calls onSortChange with selected sort', async () => {
    const mockOnChange = vi.fn();
    wrap(<GallerySortSelect sort="recent" onSortChange={mockOnChange} />);

    const popularBtn = screen.getByRole('button', { name: 'Popular' });
    await userEvent.click(popularBtn);

    expect(mockOnChange).toHaveBeenCalledWith('popular');
  });

  it('changes active state when sort prop changes', () => {
    const { rerender } = render(
      <CssVarsProvider theme={joyTheme}>
        <GallerySortSelect sort="recent" onSortChange={() => {}} />
      </CssVarsProvider>,
    );

    let recentBtn = screen.getByRole('button', { name: 'Recent' });
    expect(recentBtn).toHaveAttribute('aria-pressed', 'true');

    rerender(
      <CssVarsProvider theme={joyTheme}>
        <GallerySortSelect sort="popular" onSortChange={() => {}} />
      </CssVarsProvider>,
    );

    const popularBtn = screen.getByRole('button', { name: 'Popular' });
    expect(popularBtn).toHaveAttribute('aria-pressed', 'true');

    recentBtn = screen.getByRole('button', { name: 'Recent' });
    expect(recentBtn).toHaveAttribute('aria-pressed', 'false');
  });
});
