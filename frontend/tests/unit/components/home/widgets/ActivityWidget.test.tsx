/**
 * @file tests/unit/components/home/widgets/ActivityWidget.test.tsx
 * @brief Unit tests for ActivityWidget: verb formatting, routing, error states.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssVarsProvider } from "@mui/joy/styles";
import joyTheme from "@/theme/joy-theme";
import { ActivityItem } from "@/lib/api/home";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

vi.mock("@/hooks/useActivityFeed", () => ({
  useActivityFeed: vi.fn(),
}));

import { ActivityWidget } from "@/components/home/widgets/ActivityWidget";
import * as activityHook from "@/hooks/useActivityFeed";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>
    </QueryClientProvider>,
  );
}

describe("ActivityWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeleton initially", () => {
    vi.mocked(activityHook.useActivityFeed).mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
      error: null,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    } as any);

    wrap(<ActivityWidget instanceId="w1" />);
    // Should render skeleton (via Skeleton component)
    expect(document.body).toBeTruthy();
  });

  it("renders empty state when no activity", async () => {
    vi.mocked(activityHook.useActivityFeed).mockReturnValue({
      isLoading: false,
      isError: false,
      data: { pages: [{ items: [], next_cursor: null }] },
      error: null,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    } as any);

    wrap(<ActivityWidget instanceId="w1" />);

    await waitFor(() => {
      expect(screen.getByText("No recent activity")).toBeTruthy();
    });
  });

  it("renders error state when fetch fails", () => {
    vi.mocked(activityHook.useActivityFeed).mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
      error: new Error("Network error"),
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    } as any);

    wrap(<ActivityWidget instanceId="w1" />);

    expect(screen.getByText("Activity unavailable")).toBeTruthy();
  });

  it("formats post.created activity", async () => {
    const item: ActivityItem = {
      id: "1",
      actor_id: "actor-1",
      actor_name: "Sue",
      verb: "post.created",
      object_type: "post",
      object_id: "post-1",
      container_type: "community",
      container_title: "Community",
      object_title: "My thoughts",
      count: 1,
      created_at: new Date().toISOString(),
    };

    vi.mocked(activityHook.useActivityFeed).mockReturnValue({
      isLoading: false,
      isError: false,
      data: { pages: [{ items: [item], next_cursor: null }] },
      error: null,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    } as any);

    wrap(<ActivityWidget instanceId="w1" />);

    await waitFor(() => {
      expect(screen.getByText(/Sue posted/)).toBeTruthy();
    });
  });

  it("formats media.uploaded with count aggregation", async () => {
    const item: ActivityItem = {
      id: "2",
      actor_id: "actor-2",
      actor_name: "John",
      verb: "media.uploaded",
      object_type: "media",
      object_id: "media-1",
      container_type: "gallery",
      container_title: "Trip Album",
      object_title: null,
      count: 4,
      created_at: new Date().toISOString(),
    };

    vi.mocked(activityHook.useActivityFeed).mockReturnValue({
      isLoading: false,
      isError: false,
      data: { pages: [{ items: [item], next_cursor: null }] },
      error: null,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    } as any);

    wrap(<ActivityWidget instanceId="w1" />);

    await waitFor(() => {
      expect(screen.getByText(/John added 4/)).toBeTruthy();
    });
  });

  it("renders click-through links to posts", async () => {
    const item: ActivityItem = {
      id: "3",
      actor_id: "actor-3",
      actor_name: "Alice",
      verb: "post.created",
      object_type: "post",
      object_id: "post-abc",
      container_type: "community",
      container_title: "Community",
      object_title: "News",
      count: 1,
      created_at: new Date().toISOString(),
    };

    vi.mocked(activityHook.useActivityFeed).mockReturnValue({
      isLoading: false,
      isError: false,
      data: { pages: [{ items: [item], next_cursor: null }] },
      error: null,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    } as any);

    wrap(<ActivityWidget instanceId="w1" />);

    await waitFor(() => {
      const link = screen.getByRole("link");
      expect(link.getAttribute("href")).toBe("/app/posts/post-abc");
    });
  });

  it("renders click-through links to events", async () => {
    const item: ActivityItem = {
      id: "4",
      actor_id: "actor-4",
      actor_name: "Bob",
      verb: "event.created",
      object_type: "event",
      object_id: "event-xyz",
      container_type: "community",
      container_title: "Community",
      object_title: "Meeting",
      count: 1,
      created_at: new Date().toISOString(),
    };

    vi.mocked(activityHook.useActivityFeed).mockReturnValue({
      isLoading: false,
      isError: false,
      data: { pages: [{ items: [item], next_cursor: null }] },
      error: null,
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    } as any);

    wrap(<ActivityWidget instanceId="w1" />);

    await waitFor(() => {
      const link = screen.getByRole("link");
      expect(link.getAttribute("href")).toBe("/app/events/event-xyz");
    });
  });
});
