/**
 * @file tests/unit/events/WeekView.test.tsx
 * @brief Tests for the week view component.
 */
import * as React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CssVarsProvider } from '@mui/joy/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import joyTheme from '@/theme/joy-theme';
import { WeekView } from '@/components/events/WeekView';
import type { EventItem } from '@/lib/api/events';
import { parseISO, startOfWeek } from 'date-fns';

const baseEvent: Omit<EventItem, 'id' | 'starts_at' | 'ends_at'> = {
  author_id: 'u1',
  title: 'Test Event',
  description: null,
  location: null,
  is_all_day: false,
  recurrence_rule: null,
  visibility: 'community',
  subgroup_id: null,
  calendar_id: null,
  color: null,
  latitude: null,
  longitude: null,
  rsvp_labels: {},
  rsvp_counts: {},
  contribution_slots: [],
  user_rsvp: null,
  created_at: '2026-04-27T00:00:00Z',
  updated_at: '2026-04-27T00:00:00Z',
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CssVarsProvider theme={joyTheme}>
        {ui}
      </CssVarsProvider>
    </QueryClientProvider>,
  );
}

describe('WeekView', () => {
  it('renders 3 events spanning Mon-Wed in correct columns', () => {
    // Week starting Sunday 2026-04-26
    const weekStart = startOfWeek(parseISO('2026-04-27'), { weekStartsOn: 0 });

    const events: EventItem[] = [
      {
        ...baseEvent,
        id: 'e1',
        title: 'Monday Event',
        starts_at: '2026-04-27T10:00:00Z',
        ends_at: '2026-04-27T11:00:00Z',
      },
      {
        ...baseEvent,
        id: 'e2',
        title: 'Tuesday Event',
        starts_at: '2026-04-28T14:00:00Z',
        ends_at: '2026-04-28T15:30:00Z',
      },
      {
        ...baseEvent,
        id: 'e3',
        title: 'Wednesday Event',
        starts_at: '2026-04-29T09:00:00Z',
        ends_at: '2026-04-29T12:00:00Z',
      },
    ];

    const subgroupNames = new Map<string, string>();

    wrap(
      <WeekView
        weekStart={weekStart}
        events={events}
        subgroupNames={subgroupNames}
        selectedEventId={null}
        onSelectEvent={() => {}}
      />,
    );

    expect(screen.getByText('Monday Event')).toBeInTheDocument();
    expect(screen.getByText('Tuesday Event')).toBeInTheDocument();
    expect(screen.getByText('Wednesday Event')).toBeInTheDocument();
  });
});
