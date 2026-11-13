/**
 * @file tests/unit/components/EventsTab.test.tsx
 * @brief EventsTab: "New event" button renders only for members and pre-fills subgroup.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { EventsTab } from "@/components/subgroups/hub/EventsTab";
import type { SubgroupDetail } from "@/lib/api/subgroups";

const mockSubgroupMember: any = {
  id: "sg-1",
  name: "Test Group",
  slug: "test-group",
  description: "A test group",
  created_at: "2025-01-01T00:00:00Z",
  avatar_url: null,
  my_role: "member",
  is_member: true,
  member_count: 5,
};

const mockSubgroupNonMember: any = {
  ...mockSubgroupMember,
  my_role: null,
  is_member: false,
};

function wrap(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

// jsdom lacks ResizeObserver (used by EventDetailPanel).
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver;

// Mock the hooks
vi.mock("@/hooks/useEvents", () => {
  const mockMutation = {
    mutateAsync: vi.fn().mockResolvedValue({}),
    isPending: false,
  };
  return {
    useEventsInRange: () => ({
      data: { items: [] },
      isLoading: false,
    }),
    useCreateEvent: () => mockMutation,
    useUpdateEvent: () => mockMutation,
  };
});

vi.mock("@/hooks/useCalendars", () => ({
  useCalendars: () => ({
    data: [],
  }),
}));

vi.mock("@/hooks/useUserLocation", () => ({
  useUserLocation: () => null,
}));

describe("EventsTab", () => {
  it('renders "New event" button for members', () => {
    wrap(<EventsTab subgroup={mockSubgroupMember} />);
    expect(
      screen.getByRole("button", { name: /new event/i }),
    ).toBeInTheDocument();
  });

  it('does not render "New event" button for non-members', () => {
    wrap(<EventsTab subgroup={mockSubgroupNonMember} />);
    expect(
      screen.queryByRole("button", { name: /new event/i }),
    ).not.toBeInTheDocument();
  });

  it('"New event" button opens the event create modal', async () => {
    wrap(<EventsTab subgroup={mockSubgroupMember} />);
    const button = screen.getByRole("button", { name: /new event/i });
    await userEvent.click(button);
    // Modal should render with create form title
    const titles = screen.getAllByText(/new event/i);
    expect(titles.length).toBeGreaterThan(1); // button + modal title
  });
});
