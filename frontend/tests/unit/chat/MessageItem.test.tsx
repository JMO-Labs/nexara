/**
 * @file tests/unit/chat/MessageItem.test.tsx
 * @brief Author + content rendering, deleted styling, edited marker.
 */
import * as React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CssVarsProvider } from '@mui/joy/styles';
import joyTheme from '@/theme/joy-theme';
import { MessageItem } from '@/components/chat/MessageItem';
import type { ChatMessage } from '@/lib/api/chat';

const author = { id: 'u1', username: 'alex', display_name: 'Alex', avatar_url: null };
const base: ChatMessage = {
  id: 'm1',
  channel_id: 'c1',
  author,
  content: 'hello',
  edited_at: null,
  deleted: false,
  created_at: new Date('2026-04-25T15:00:00Z').toISOString(),
};

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

describe('MessageItem', () => {
  it('renders author + content', () => {
    wrap(<MessageItem message={base} />);
    expect(screen.getByText('Alex')).toBeInTheDocument();
    expect(screen.getByText('hello')).toBeInTheDocument();
  });

  it('shows edited marker', () => {
    wrap(<MessageItem message={{ ...base, edited_at: base.created_at }} />);
    expect(screen.getByText(/edited/i)).toBeInTheDocument();
  });

  it('hides author in compact mode', () => {
    wrap(<MessageItem message={base} compact />);
    expect(screen.queryByText('Alex')).not.toBeInTheDocument();
  });
});
