/**
 * @file tests/unit/components/EventCreateModal.test.tsx
 * @brief EventCreateModal: defaultSubgroupId pre-fills visibility and subgroupId in create mode.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CssVarsProvider } from '@mui/joy/styles';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import joyTheme from '@/theme/joy-theme';
import { EventCreateModal } from '@/components/events/EventCreateModal';

const mockCalendars = [
  { id: 'cal-1', kind: 'subgroup' as const, name: 'My Group', subgroup_id: 'sg-1' },
  { id: 'cal-2', kind: 'subgroup' as const, name: 'Other Group', subgroup_id: 'sg-2' },
];

function wrap(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
    </QueryClientProvider>,
  );
}

// Mock the hooks
vi.mock('@/hooks/useEvents', () => {
  const mockMutation = {
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  };
  return {
    useCreateEvent: () => mockMutation,
    useUpdateEvent: () => mockMutation,
  };
});

vi.mock('@/hooks/useCalendars', () => ({
  useCalendars: () => ({
    data: mockCalendars,
  }),
}));

vi.mock('@/hooks/useUserLocation', () => ({
  useUserLocation: () => null,
}));

describe('EventCreateModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders in create mode when open with no event', async () => {
    wrap(
      <EventCreateModal
        open={true}
        onClose={vi.fn()}
        defaultSubgroupId="sg-1"
      />,
    );
    await waitFor(() => {
      expect(screen.getByText(/new event/i)).toBeInTheDocument();
    });
  });

  it('pre-fills visibility to "subgroup" when defaultSubgroupId provided in create mode', async () => {
    wrap(
      <EventCreateModal
        open={true}
        onClose={vi.fn()}
        defaultSubgroupId="sg-1"
      />,
    );
    await waitFor(() => {
      const visibilitySelect = screen.getByDisplayValue(/group/i);
      expect(visibilitySelect).toBeInTheDocument();
    });
  });

  it('defaults to "community" visibility when no defaultSubgroupId in create mode', async () => {
    wrap(
      <EventCreateModal
        open={true}
        onClose={vi.fn()}
      />,
    );
    await waitFor(() => {
      const visibilitySelect = screen.getByDisplayValue(/community/i);
      expect(visibilitySelect).toBeInTheDocument();
    });
  });

  it('ignores defaultSubgroupId when editing an event', async () => {
    const mockEvent: any = {
      id: 'evt-1',
      title: 'Existing Event',
      description: '',
      location: '',
      starts_at: '2025-05-01T10:00:00Z',
      ends_at: '2025-05-01T11:00:00Z',
      is_all_day: false,
      visibility: 'community' as const,
      subgroup_id: null,
      color: null,
      latitude: null,
      longitude: null,
    };

    wrap(
      <EventCreateModal
        open={true}
        onClose={vi.fn()}
        event={mockEvent}
        defaultSubgroupId="sg-1"
      />,
    );
    await waitFor(() => {
      expect(screen.getByText(/edit event/i)).toBeInTheDocument();
      const visibilitySelect = screen.getByDisplayValue(/community/i);
      expect(visibilitySelect).toBeInTheDocument();
    });
  });
});
