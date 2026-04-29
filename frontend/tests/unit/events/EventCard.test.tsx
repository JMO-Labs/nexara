/**
 * @file tests/unit/events/EventCard.test.tsx
 * @brief Renders event title + schedule + RSVP chips.
 */
import * as React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CssVarsProvider } from '@mui/joy/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import joyTheme from '@/theme/joy-theme';
import { EventCard } from '@/components/events/EventCard';
import type { EventItem } from '@/lib/api/events';

vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      'toasts.events.rsvp.saved': 'RSVP saved',
      'toasts.errors.generic': 'Something went wrong',
    };
    return translations[key] || key;
  },
}));

vi.mock('@/lib/api/events', async (orig) => ({
  ...(await orig<typeof import('@/lib/api/events')>()),
  rsvpEvent: vi.fn(),
  unrsvpEvent: vi.fn(),
}));

const ev: EventItem = {
  id: 'e1',
  author_id: 'u1',
  title: 'Picnic',
  description: 'Bring food',
  location: 'Park',
  starts_at: '2026-05-01T18:00:00Z',
  ends_at: '2026-05-01T20:00:00Z',
  is_all_day: false,
  recurrence_rule: null,
  visibility: 'community',
  subgroup_id: null,
  subgroup_slug: null,
  calendar_id: null,
  color: null,
  latitude: null,
  longitude: null,
  rsvp_labels: { attending: 'Going', maybe: 'Maybe' },
  rsvp_counts: { attending: 3 },
  contribution_slots: [],
  user_rsvp: { status: 'attending' },
  created_at: '2026-04-25T00:00:00Z',
  updated_at: '2026-04-25T00:00:00Z',
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
    </QueryClientProvider>,
  );
}

describe('EventCard', () => {
  it('renders title, location, RSVP labels and counts', () => {
    wrap(<EventCard event={ev} />);
    expect(screen.getByText('Picnic')).toBeInTheDocument();
    expect(screen.getByText(/Park/)).toBeInTheDocument();
    expect(screen.getByText(/Going · 3/)).toBeInTheDocument();
    expect(screen.getByText(/Maybe/)).toBeInTheDocument();
  });
});
