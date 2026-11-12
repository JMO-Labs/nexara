/**
 * @file tests/unit/search/GlobalCommandPalette.test.tsx
 * @brief Verify GlobalCommandPalette debounces, fetches, renders results, and navigates.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GlobalCommandPalette } from "@/components/search/GlobalCommandPalette";
import { useUI } from "@/stores/ui";

// jsdom lacks APIs cmdk relies on.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver;
Element.prototype.scrollIntoView ??= () => {};

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/hooks/useSearch", () => ({
  useGlobalSearch: vi.fn(),
}));

import { useGlobalSearch } from "@/hooks/useSearch";

describe("GlobalCommandPalette", () => {
  let qc: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
    qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    useUI.getState().setCommandPaletteOpen(false);
  });

  it("opens when useUI.commandPaletteOpen is true", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { items: [], next_cursor: null, has_more: false },
      isLoading: false,
    });

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    act(() => useUI.getState().setCommandPaletteOpen(true));
    await waitFor(() => {
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });
  });

  it("renders navigation items on open", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { items: [], next_cursor: null, has_more: false },
      isLoading: false,
    });

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    act(() => useUI.getState().setCommandPaletteOpen(true));
    await waitFor(() => {
      expect(screen.getByText("Home")).toBeInTheDocument();
    });
  });

  it("debounces input and calls useGlobalSearch after 250ms", async () => {
    const mockUseGlobalSearch = vi.fn(() => ({
      data: { items: [], next_cursor: null, has_more: false },
      isLoading: false,
    }));
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockImplementation(
      mockUseGlobalSearch,
    );

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByRole("combobox");
    const user = userEvent.setup();
    await user.type(input, "he");

    // Verify hook is called with debounced value after typing
    await waitFor(
      () => {
        const calls = mockUseGlobalSearch.mock.calls;
        expect(calls.some((c) => c?.at(0) === "he")).toBe(true);
      },
      { timeout: 500 },
    );
  });

  it("renders search results with correct navigation paths", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        items: [
          {
            id: "p1",
            type: "posts",
            title: "My Post",
            snippet: "Post content",
            created_at: "2026-04-25T00:00:00Z",
          },
        ],
        next_cursor: null,
        has_more: false,
      },
      isLoading: false,
    });

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByRole("combobox");
    const user = userEvent.setup();
    await user.type(input, "post");

    await waitFor(() => {
      expect(screen.getByText("My Post")).toBeInTheDocument();
    });
  });

  it("navigates to post when post result selected", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        items: [
          {
            id: "p1",
            type: "posts",
            title: "My Post",
            snippet: "Post content",
            created_at: "2026-04-25T00:00:00Z",
          },
        ],
        next_cursor: null,
        has_more: false,
      },
      isLoading: false,
    });

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByRole("combobox");
    const user = userEvent.setup();
    await user.type(input, "post");

    await waitFor(() => {
      const item = screen.getByText("My Post");
      expect(item).toBeInTheDocument();
    });

    const item = screen.getByText("My Post").closest('[role="option"]');
    await user.click(item!);

    expect(mockPush).toHaveBeenCalledWith("/app/post/p1");
  });

  it("navigates to user when user result selected", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        items: [
          {
            id: "u1",
            type: "users",
            title: "John Doe",
            snippet: "user@example.com",
            created_at: "2026-04-25T00:00:00Z",
          },
        ],
        next_cursor: null,
        has_more: false,
      },
      isLoading: false,
    });

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByRole("combobox");
    const user = userEvent.setup();
    await user.type(input, "john");

    await waitFor(() => {
      const item = screen.getByText("John Doe").closest('[role="option"]');
      expect(item).toBeInTheDocument();
    });

    const item = screen.getByText("John Doe").closest('[role="option"]');
    await user.click(item!);

    expect(mockPush).toHaveBeenCalledWith("/app/members?user=u1");
  });

  it("navigates to event when event result selected", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        items: [
          {
            id: "e1",
            type: "events",
            title: "Party Time",
            snippet: "A fun event",
            created_at: "2026-04-25T00:00:00Z",
          },
        ],
        next_cursor: null,
        has_more: false,
      },
      isLoading: false,
    });

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByRole("combobox");
    const user = userEvent.setup();
    await user.type(input, "party");

    await waitFor(() => {
      const item = screen.getByText("Party Time").closest('[role="option"]');
      expect(item).toBeInTheDocument();
    });

    const item = screen.getByText("Party Time").closest('[role="option"]');
    await user.click(item!);

    expect(mockPush).toHaveBeenCalledWith("/app/events?event=e1");
  });

  it.each([
    ["polls", { id: "p1", parent_id: "post9" }, "/app/post/post9"],
    ["galleries", { id: "g1" }, "/app/galleries?gallery=g1"],
    ["subgroups", { id: "s1", slug: "choir" }, "/app/subgroups/choir"],
  ])("navigates for %s result", async (type, extra, href) => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        items: [
          {
            type,
            title: "Target Row",
            snippet: "s",
            created_at: "2026-04-25T00:00:00Z",
            ...extra,
          },
        ],
        next_cursor: null,
        has_more: false,
      },
      isLoading: false,
    });
    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );
    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByRole("combobox");
    const user = userEvent.setup();
    await user.type(input, "target");
    const item = (await screen.findByText("Target Row")).closest(
      '[role="option"]',
    );
    await user.click(item!);
    expect(mockPush).toHaveBeenCalledWith(href);
  });

  it("navigates to post with comment anchor when comment result selected", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        items: [
          {
            id: "c1",
            type: "comments",
            title: "Comment reply",
            snippet: "Great post!",
            created_at: "2026-04-25T00:00:00Z",
            parent_id: "p1",
          },
        ],
        next_cursor: null,
        has_more: false,
      },
      isLoading: false,
    });

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByRole("combobox");
    const user = userEvent.setup();
    await user.type(input, "comment");

    await waitFor(() => {
      const item = screen.getByText("Comment reply").closest('[role="option"]');
      expect(item).toBeInTheDocument();
    });

    const item = screen.getByText("Comment reply").closest('[role="option"]');
    await user.click(item!);

    expect(mockPush).toHaveBeenCalledWith("/app/post/p1#comment-c1");
  });

  it("closes palette after navigation", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: {
        items: [
          {
            id: "p1",
            type: "posts",
            title: "My Post",
            snippet: "Post content",
            created_at: "2026-04-25T00:00:00Z",
          },
        ],
        next_cursor: null,
        has_more: false,
      },
      isLoading: false,
    });

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByRole("combobox");
    const user = userEvent.setup();
    await user.type(input, "post");

    await waitFor(() => {
      const item = screen.getByText("My Post").closest('[role="option"]');
      expect(item).toBeInTheDocument();
    });

    const item = screen.getByText("My Post").closest('[role="option"]');
    await user.click(item!);

    await waitFor(() => {
      expect(useUI.getState().commandPaletteOpen).toBe(false);
    });
  });

  it("navigates when navigation item is clicked", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { items: [], next_cursor: null, has_more: false },
      isLoading: false,
    });

    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );

    act(() => useUI.getState().setCommandPaletteOpen(true));
    const input = await screen.findByRole("combobox");
    const user = userEvent.setup();

    await waitFor(() => {
      const home = screen.getByText("Home").closest('[role="option"]');
      expect(home).toBeInTheDocument();
    });

    const home = screen.getByText("Home").closest('[role="option"]');
    await user.click(home!);

    expect(mockPush).toHaveBeenCalledWith("/app");
  });
});

describe("GlobalCommandPalette hotkey", () => {
  it("Ctrl+K toggles open state", async () => {
    (useGlobalSearch as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { items: [], next_cursor: null, has_more: false },
      isLoading: false,
    });
    const qc = new QueryClient();
    useUI.getState().setCommandPaletteOpen(false);
    render(
      <QueryClientProvider client={qc}>
        <GlobalCommandPalette />
      </QueryClientProvider>,
    );
    await userEvent.keyboard("{Control>}k{/Control}");
    await waitFor(() => expect(useUI.getState().commandPaletteOpen).toBe(true));
  });
});
