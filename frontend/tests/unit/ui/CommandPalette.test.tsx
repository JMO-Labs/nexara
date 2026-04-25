/**
 * @file tests/unit/ui/CommandPalette.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CssVarsProvider } from '@mui/joy/styles';
import joyTheme from '@/theme/joy-theme';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { useUI } from '@/stores/ui';

describe('CommandPalette', () => {
  beforeEach(() => useUI.getState().setCommandPaletteOpen(false));

  it('filters and selects on Enter', async () => {
    const onFeed = vi.fn();
    const onChat = vi.fn();
    render(
      <CssVarsProvider theme={joyTheme}>
        <CommandPalette
          items={[
            { id: 'feed', label: 'Open Feed', group: 'Navigate', onSelect: onFeed },
            { id: 'chat', label: 'Open Chat', group: 'Navigate', onSelect: onChat },
          ]}
        />
      </CssVarsProvider>,
    );
    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByLabelText(/command palette/i);
    await userEvent.type(input, 'chat');
    await userEvent.keyboard('{Enter}');
    expect(onChat).toHaveBeenCalledOnce();
    expect(onFeed).not.toHaveBeenCalled();
  });
});
