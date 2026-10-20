/**
 * @file tests/unit/hooks/useActivityFeed.test.ts
 * @brief Tests for useActivityFeed React Query hook.
 *
 * Tests pagination, error handling, and refetch.
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { useActivityFeed } from "@/hooks/useActivityFeed";
import * as homeApi from "@/lib/api/home";

// Mock the API
vi.mock("@/lib/api/home", () => ({
  getHomeActivity: vi.fn(),
}));

describe("useActivityFeed", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("should fetch initial page of activity", async () => {
    const mockResponse = {
      items: [
        {
          id: "1",
          actor_id: "actor-1",
          actor_name: "Sue",
          verb: "post.created",
          object_type: "post",
          object_id: "post-1",
          container_type: "community",
          container_title: "Community",
          object_title: "My Post",
          count: 1,
          created_at: "2026-04-30T10:00:00Z",
        },
      ],
      next_cursor: null,
    };

    vi.mocked(homeApi.getHomeActivity).mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useActivityFeed({ limit: 30 }), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.pages[0].items).toHaveLength(1);
    expect(result.current.data?.pages[0].items[0].actor_name).toBe("Sue");
  });

  it("should handle pagination with cursor", async () => {
    const firstPage = {
      items: [
        {
          id: "1",
          actor_id: "actor-1",
          actor_name: "Sue",
          verb: "post.created",
          object_type: "post",
          object_id: "post-1",
          container_type: "community",
          container_title: "Community",
          object_title: "First Post",
          count: 1,
          created_at: "2026-04-30T10:00:00Z",
        },
      ],
      next_cursor: "2026-04-30T09:00:00Z",
    };

    const secondPage = {
      items: [
        {
          id: "2",
          actor_id: "actor-2",
          actor_name: "John",
          verb: "event.created",
          object_type: "event",
          object_id: "event-1",
          container_type: "community",
          container_title: "Community",
          object_title: "Meeting",
          count: 1,
          created_at: "2026-04-30T09:00:00Z",
        },
      ],
      next_cursor: null,
    };

    vi.mocked(homeApi.getHomeActivity)
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage);

    const { result } = renderHook(() => useActivityFeed({ limit: 30 }), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.pages[0].items).toHaveLength(1);
    expect(result.current.hasNextPage).toBe(true);

    // Fetch next page
    result.current.fetchNextPage();

    await waitFor(() => {
      expect(result.current.data?.pages).toHaveLength(2);
    });

    expect(result.current.data?.pages[1].items[0].actor_name).toBe("John");
  });

  it("should handle errors", async () => {
    const error = new Error("Network error");
    vi.mocked(homeApi.getHomeActivity).mockRejectedValueOnce(error);

    const { result } = renderHook(() => useActivityFeed({ limit: 30 }), {
      wrapper,
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });

  it("should refetch when cursor is updated", async () => {
    const mockResponse = {
      items: [],
      next_cursor: null,
    };

    vi.mocked(homeApi.getHomeActivity).mockResolvedValue(mockResponse);

    const { result, rerender } = renderHook((props) => useActivityFeed(props), {
      wrapper,
      initialProps: { limit: 30 },
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    const callCount1 = vi.mocked(homeApi.getHomeActivity).mock.calls.length;

    // Refetch
    result.current.refetch();

    await waitFor(() => {
      expect(
        vi.mocked(homeApi.getHomeActivity).mock.calls.length,
      ).toBeGreaterThan(callCount1);
    });
  });
});
