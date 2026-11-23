/**
 * @file tests/unit/components/events/eventDeepLink.test.tsx
 * @brief `/app/events?event=<id>` deep links open the event's own page.
 */
import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams("event=ev 1"),
}));
vi.mock("@/hooks/useEvents", () => ({
  useEventsInRange: () => ({ data: [] }),
}));
vi.mock("@/hooks/useSubgroups", () => ({
  useSubgroupList: () => ({ data: [] }),
}));
vi.mock("@/hooks/useCalendars", () => ({ useCalendars: () => ({ data: [] }) }));
vi.mock("@tanstack/react-query", () => ({ useQuery: () => ({ data: [] }) }));

import { useEventsPageState } from "@/components/events/events-page/useEventsPageState";

describe("event deep link", () => {
  it("replaces the URL with the event page", () => {
    renderHook(() => useEventsPageState());
    expect(replace).toHaveBeenCalledWith("/app/events/ev%201");
  });
});
