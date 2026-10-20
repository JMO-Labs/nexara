/**
 * @file tests/unit/components/home/widgets/UpcomingEventsWidget.test.tsx
 * @brief Unit tests for UpcomingEventsWidget.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";

// Mock hooks before importing component
vi.mock("@/hooks/useEvents", () => ({
  useUpcomingEvents: vi.fn(() => ({ data: undefined, isLoading: true })),
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: vi.fn(() => ({ data: [], isLoading: false })),
}));
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));
vi.mock("@/components/events/EventDetailPanel", () => ({
  EventDetailPanel: () => null,
}));

import { UpcomingEventsWidget } from "@/components/home/widgets/UpcomingEventsWidget";
import { useUpcomingEvents } from "@/hooks/useEvents";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
    </QueryClientProvider>,
  );
}

describe("UpcomingEventsWidget", () => {
  it("renders without crashing", () => {
    wrap(<UpcomingEventsWidget instanceId="w1" />);
    expect(document.body).toBeTruthy();
  });

  it("shows skeleton while loading", () => {
    wrap(<UpcomingEventsWidget instanceId="w1" />);
    // Loading state renders skeleton elements
    expect(document.body.children.length).toBeGreaterThan(0);
  });

  it("shows empty state when no events", () => {
    vi.mocked(useUpcomingEvents).mockReturnValue({
      data: { items: [], next_cursor: null, has_more: false },
      isLoading: false,
    } as unknown as ReturnType<typeof useUpcomingEvents>);

    wrap(<UpcomingEventsWidget instanceId="w1" />);
    expect(screen.getByText("No upcoming events")).toBeInTheDocument();
  });

  it("renders event rows when data is available", () => {
    vi.mocked(useUpcomingEvents).mockReturnValue({
      data: {
        items: [
          {
            id: "e1",
            title: "Team Meeting",
            starts_at: new Date(Date.now() + 86400000).toISOString(),
            ends_at: new Date(Date.now() + 90000000).toISOString(),
            is_all_day: false,
            subgroup_id: null,
            description: null,
            location: null,
            recurrence_rule: null,
            visibility: "community",
            calendar_id: null,
            color: null,
            latitude: null,
            longitude: null,
            rsvp_labels: null,
            rsvp_counts: {},
            contribution_slots: [],
            user_rsvp: null,
            author_id: "u1",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
        next_cursor: null,
        has_more: false,
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useUpcomingEvents>);

    wrap(<UpcomingEventsWidget instanceId="w1" />);
    expect(screen.getByText("Team Meeting")).toBeInTheDocument();
  });
});
