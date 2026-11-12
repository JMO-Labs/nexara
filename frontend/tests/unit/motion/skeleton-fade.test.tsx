/**
 * @file tests/unit/motion/skeleton-fade.test.tsx
 * @brief EventList and MessageList skeleton states fade, EventList items
 *        stagger in on initial load; reduced motion skips all of it.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

let reduced = false;
vi.mock("framer-motion", async () => {
  const actual =
    await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return { ...actual, useReducedMotion: () => reduced };
});
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));
const events = vi.hoisted(() => ({
  value: { data: undefined as unknown, isLoading: true, error: null },
}));
vi.mock("@/hooks/useEvents", () => ({
  useUpcomingEvents: () => events.value,
}));
vi.mock("@/components/events/EventCard", () => ({
  EventCard: ({ event }: { event: { id: string } }) => (
    <div data-testid="event-card">{event.id}</div>
  ),
}));

import { EventList } from "@/components/events/EventList";
import { MessageList } from "@/components/chat/MessageList";

const loaded = {
  data: {
    items: [
      { id: "e1", starts_at: "2026-12-01T10:00:00Z" },
      { id: "e2", starts_at: "2026-12-02T10:00:00Z" },
    ],
  },
  isLoading: false,
  error: null,
};

beforeEach(() => {
  reduced = false;
  events.value = { data: undefined, isLoading: true, error: null };
});

describe("EventList skeleton fade", () => {
  it("fades skeleton in", () => {
    render(<EventList />);
    expect(screen.getByTestId("event-skeleton")).toHaveStyle({ opacity: "0" });
  });
  it("skips under reduced motion", () => {
    reduced = true;
    render(<EventList />);
    expect(screen.getByTestId("event-skeleton").style.opacity).toBe("");
  });
});

describe("EventList initial-load stagger", () => {
  it("items start hidden", () => {
    events.value = loaded;
    render(<EventList />);
    const items = screen.getAllByTestId("event-card");
    expect(items).toHaveLength(2);
    expect(items[0].parentElement).toHaveStyle({ opacity: "0" });
  });
  it("items render with no style under reduced motion", () => {
    reduced = true;
    events.value = loaded;
    render(<EventList />);
    const item = screen.getAllByTestId("event-card")[0].parentElement!;
    expect(item.style.opacity).toBe("");
    expect(item.style.transform).toBe("");
  });
});

describe("MessageList skeleton fade", () => {
  const list = () => (
    <MessageList
      messages={[]}
      isLoading
      hasMore={false}
      isFetchingMore={false}
      onLoadMore={vi.fn()}
    />
  );
  it("fades skeleton in", () => {
    render(list());
    expect(screen.getByTestId("message-skeleton")).toHaveStyle({
      opacity: "0",
    });
  });
  it("skips under reduced motion", () => {
    reduced = true;
    render(list());
    expect(screen.getByTestId("message-skeleton").style.opacity).toBe("");
  });
});
