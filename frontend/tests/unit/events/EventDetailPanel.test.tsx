/**
 * @file tests/unit/events/EventDetailPanel.test.tsx
 * @brief Tests for EventDetailPanel — map embedding when geo coords present.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EventDetailPanel } from "@/components/events/EventDetailPanel";
import type { EventItem } from "@/lib/api/events";

// Mock ResizeObserver (jsdom doesn't provide it)
beforeAll(() => {
  class MockResizeObserver {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  global.ResizeObserver = MockResizeObserver as any;
});

// Mock EventMiniMap to avoid Leaflet loading in jsdom
vi.mock("@/components/events/EventMiniMap", () => ({
  EventMiniMap: ({
    lat,
    lon,
    height,
  }: {
    lat: number;
    lon: number;
    height?: number;
  }) => (
    <div
      data-testid="event-mini-map"
      data-lat={lat}
      data-lon={lon}
      data-height={height}
    >
      Map
    </div>
  ),
  default: ({
    lat,
    lon,
    height,
  }: {
    lat: number;
    lon: number;
    height?: number;
  }) => (
    <div
      data-testid="event-mini-map"
      data-lat={lat}
      data-lon={lon}
      data-height={height}
    >
      Map
    </div>
  ),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/hooks/useEvents", () => ({
  useDeleteEvent: () => ({ mutate: vi.fn(), isPending: false }),
  useRsvp: () => ({ mutate: vi.fn(), isPending: false }),
  useClaimContribution: () => ({ mutate: vi.fn(), isPending: false }),
  useUnclaimContribution: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/stores/session", () => ({
  useSession: () => null,
}));

const baseEvent: EventItem = {
  id: "e1",
  author_id: "u1",
  title: "Test Event",
  description: "A test event",
  location: "Downtown Park",
  starts_at: "2026-05-01T18:00:00Z",
  ends_at: "2026-05-01T20:00:00Z",
  is_all_day: false,
  recurrence_rule: null,
  visibility: "community",
  subgroup_id: null,
  subgroup_slug: null,
  calendar_id: null,
  color: null,
  latitude: null,
  longitude: null,
  rsvp_labels: { attending: "Going", maybe: "Maybe" },
  rsvp_counts: { attending: 2 },
  contribution_slots: [],
  user_rsvp: null,
  created_at: "2026-04-25T00:00:00Z",
  updated_at: "2026-04-25T00:00:00Z",
};

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("EventDetailPanel", () => {
  it("renders EventMiniMap when event has latitude and longitude", async () => {
    const containerRef = React.createRef<HTMLDivElement>();
    const event: EventItem = {
      ...baseEvent,
      latitude: 40.7128,
      longitude: -74.006,
    };

    wrap(
      <div ref={containerRef} style={{ width: 400 }}>
        <EventDetailPanel
          containerRef={containerRef}
          event={event}
          subgroupNames={new Map()}
          onClose={vi.fn()}
        />
      </div>,
    );

    await waitFor(() => {
      const map = screen.getByTestId("event-mini-map");
      expect(map).toBeInTheDocument();
      expect(map).toHaveAttribute("data-lat", "40.7128");
      expect(map).toHaveAttribute("data-lon", "-74.006");
    });
  });

  it("does not render EventMiniMap when latitude is null", () => {
    const containerRef = React.createRef<HTMLDivElement>();
    const event: EventItem = {
      ...baseEvent,
      latitude: null,
      longitude: -74.006,
    };

    wrap(
      <div ref={containerRef} style={{ width: 400 }}>
        <EventDetailPanel
          containerRef={containerRef}
          event={event}
          subgroupNames={new Map()}
          onClose={vi.fn()}
        />
      </div>,
    );

    const map = screen.queryByTestId("event-mini-map");
    expect(map).not.toBeInTheDocument();
  });

  it("does not render EventMiniMap when longitude is null", () => {
    const containerRef = React.createRef<HTMLDivElement>();
    const event: EventItem = {
      ...baseEvent,
      latitude: 40.7128,
      longitude: null,
    };

    wrap(
      <div ref={containerRef} style={{ width: 400 }}>
        <EventDetailPanel
          containerRef={containerRef}
          event={event}
          subgroupNames={new Map()}
          onClose={vi.fn()}
        />
      </div>,
    );

    const map = screen.queryByTestId("event-mini-map");
    expect(map).not.toBeInTheDocument();
  });

  it('renders "Open in Google Maps" link when event has location and coordinates', async () => {
    const containerRef = React.createRef<HTMLDivElement>();
    const event: EventItem = {
      ...baseEvent,
      latitude: 40.7128,
      longitude: -74.006,
    };

    wrap(
      <div ref={containerRef} style={{ width: 400 }}>
        <EventDetailPanel
          containerRef={containerRef}
          event={event}
          subgroupNames={new Map()}
          onClose={vi.fn()}
        />
      </div>,
    );

    await waitFor(() => {
      const link = screen.getByRole("link", { name: /Open in Google Maps/i });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute("target", "_blank");
    });
  });
});
