/**
 * @file tests/unit/events/useEvents.test.tsx
 * @brief useCreateEvent invalidates events.all on success.
 */
import * as React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { useToasts } from "@/stores/toasts";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      "toasts.events.created": "Event created",
      "toasts.events.rsvp.saved": "RSVP saved",
      "toasts.errors.generic": "Something went wrong",
    };
    return translations[key] || key;
  },
}));

vi.mock("@/lib/api/events", () => ({
  listEvents: vi.fn(),
  getEvent: vi.fn(),
  createEvent: vi.fn(),
  updateEvent: vi.fn(),
  deleteEvent: vi.fn(),
  rsvpEvent: vi.fn(),
  unrsvpEvent: vi.fn(),
}));

import * as api from "@/lib/api/events";
import { useCreateEvent, useRsvp } from "@/hooks/useEvents";

function wrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useEvents mutations", () => {
  let qc: QueryClient;
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
    qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  });

  it("useCreateEvent invalidates events.all", async () => {
    (api.createEvent as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "e1",
    });
    const spy = vi.spyOn(qc, "invalidateQueries");
    const { result } = renderHook(() => useCreateEvent(), {
      wrapper: wrapper(qc),
    });
    await act(async () => {
      await result.current.mutateAsync({
        title: "t",
        starts_at: "2026-05-01T00:00:00Z",
        ends_at: "2026-05-01T01:00:00Z",
      });
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: qk.events.all() });
  });

  it("useRsvp routes to rsvpEvent for status, unrsvpEvent for null", async () => {
    (api.rsvpEvent as ReturnType<typeof vi.fn>).mockResolvedValue({
      status: "attending",
    });
    (api.unrsvpEvent as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: "ok",
    });
    const { result } = renderHook(() => useRsvp("e1"), {
      wrapper: wrapper(qc),
    });
    await act(async () => {
      await result.current.mutateAsync("attending");
    });
    expect(api.rsvpEvent).toHaveBeenCalledWith("e1", "attending");
    await act(async () => {
      await result.current.mutateAsync(null);
    });
    expect(api.unrsvpEvent).toHaveBeenCalledWith("e1");
  });
});
