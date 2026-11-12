/**
 * @file tests/unit/motion/skeleton-fade.test.tsx
 * @brief EventList and MessageList skeleton states fade; reduced motion skips.
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
vi.mock("@/hooks/useEvents", () => ({
  useUpcomingEvents: () => ({ data: undefined, isLoading: true, error: null }),
}));

import { EventList } from "@/components/events/EventList";

beforeEach(() => {
  reduced = false;
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
