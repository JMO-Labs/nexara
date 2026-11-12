/**
 * @file tests/unit/hooks/useCalendarSubscriptions.test.tsx
 * @brief Unit tests for calendar subscription hooks.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { act, waitFor } from "@testing-library/react";

import * as eventsApi from "@/lib/api/events";
import {
  useCalendarSubscriptions,
  useAddSubscription,
  useUpdateSubscription,
  useDeleteSubscription,
  useSyncNow,
} from "@/hooks/useCalendarSubscriptions";
import { qk } from "@/lib/query-keys";
import { renderHookWithProviders } from "../../utils/renderWithProviders";

vi.mock("@/lib/api/events");
vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));

const listKey = { queryKey: qk.events.subscriptions.list() };

describe("useCalendarSubscriptions", () => {
  beforeEach(() => vi.clearAllMocks());

  it("lists subscriptions", async () => {
    const data = [{ id: "s1" }] as never;
    vi.mocked(eventsApi.listSubscriptions).mockResolvedValue(data);
    const { result } = renderHookWithProviders(() =>
      useCalendarSubscriptions(),
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBe(data);
  });

  it("exposes error state", async () => {
    vi.mocked(eventsApi.listSubscriptions).mockRejectedValue(new Error("no"));
    const { result } = renderHookWithProviders(() =>
      useCalendarSubscriptions(),
    );
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("subscription mutations", () => {
  beforeEach(() => vi.clearAllMocks());

  it("useAddSubscription creates and invalidates list", async () => {
    vi.mocked(eventsApi.createSubscription).mockResolvedValue({} as never);
    const { result, queryClient } = renderHookWithProviders(() =>
      useAddSubscription(),
    );
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    const body = { url: "https://x/y.ics" } as never;
    await act(async () => {
      await result.current.mutateAsync(body);
    });
    expect(vi.mocked(eventsApi.createSubscription).mock.calls[0][0]).toBe(body);
    expect(spy).toHaveBeenCalledWith(listKey);
  });

  it("useUpdateSubscription updates by id with body and invalidates list", async () => {
    vi.mocked(eventsApi.updateSubscription).mockResolvedValue({} as never);
    const { result, queryClient } = renderHookWithProviders(() =>
      useUpdateSubscription(),
    );
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    const body = { name: "Renamed", enabled: false } as never;
    await act(async () => {
      await result.current.mutateAsync({ id: "s1", body });
    });
    expect(eventsApi.updateSubscription).toHaveBeenCalledWith("s1", body);
    expect(spy).toHaveBeenCalledWith(listKey);
  });

  it("useDeleteSubscription deletes by id and invalidates list", async () => {
    vi.mocked(eventsApi.deleteSubscription).mockResolvedValue(
      undefined as never,
    );
    const { result, queryClient } = renderHookWithProviders(() =>
      useDeleteSubscription(),
    );
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    await act(async () => {
      await result.current.mutateAsync("s1");
    });
    expect(vi.mocked(eventsApi.deleteSubscription).mock.calls[0][0]).toBe("s1");
    expect(spy).toHaveBeenCalledWith(listKey);
  });

  it("useSyncNow syncs by id and invalidates list", async () => {
    vi.mocked(eventsApi.syncNowSubscription).mockResolvedValue({} as never);
    const { result, queryClient } = renderHookWithProviders(() => useSyncNow());
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    await act(async () => {
      await result.current.mutateAsync("s2");
    });
    expect(vi.mocked(eventsApi.syncNowSubscription).mock.calls[0][0]).toBe(
      "s2",
    );
    expect(spy).toHaveBeenCalledWith(listKey);
  });

  it("does not invalidate when a mutation fails", async () => {
    vi.mocked(eventsApi.deleteSubscription).mockRejectedValue(new Error("x"));
    const { result, queryClient } = renderHookWithProviders(() =>
      useDeleteSubscription(),
    );
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    await act(async () => {
      await result.current.mutateAsync("s1").catch(() => undefined);
    });
    expect(spy).not.toHaveBeenCalled();
  });
});
