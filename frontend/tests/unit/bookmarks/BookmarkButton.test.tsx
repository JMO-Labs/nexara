/**
 * @file tests/unit/bookmarks/BookmarkButton.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useToasts } from "@/stores/toasts";

vi.mock("@/lib/api/bookmarks", () => ({
  toggleBookmark: vi.fn(),
  listBookmarks: vi.fn(),
}));
import * as api from "@/lib/api/bookmarks";
import { BookmarkButton } from "@/components/feed/BookmarkButton";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  vi.resetAllMocks();
  useToasts.getState().clear();
});

describe("BookmarkButton", () => {
  it("reflects state via aria-pressed", () => {
    wrap(<BookmarkButton postId="p1" isBookmarked />);
    expect(screen.getByRole("button", { name: /bookmark/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("updates optimistically and toasts success", async () => {
    vi.mocked(api.toggleBookmark).mockImplementation(
      () => new Promise(() => {}),
    );
    wrap(<BookmarkButton postId="p1" isBookmarked={false} />);
    fireEvent.click(screen.getByRole("button", { name: /bookmark/i }));
    expect(screen.getByRole("button", { name: /bookmark/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(api.toggleBookmark).toHaveBeenCalledWith("p1");
  });

  it("reverts and shows error toast on failure", async () => {
    vi.mocked(api.toggleBookmark).mockRejectedValue(new Error("boom"));
    wrap(<BookmarkButton postId="p1" isBookmarked={false} />);
    fireEvent.click(screen.getByRole("button", { name: /bookmark/i }));
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /bookmark/i }),
      ).toHaveAttribute("aria-pressed", "false"),
    );
    expect(useToasts.getState().items.some((t) => t.variant === "danger")).toBe(
      true,
    );
  });

  it("toasts success after server confirms", async () => {
    vi.mocked(api.toggleBookmark).mockResolvedValue({
      post_id: "p1",
      is_bookmarked: true,
    });
    wrap(<BookmarkButton postId="p1" isBookmarked={false} />);
    fireEvent.click(screen.getByRole("button", { name: /bookmark/i }));
    await waitFor(() =>
      expect(
        useToasts.getState().items.some((t) => t.variant === "success"),
      ).toBe(true),
    );
  });
});
