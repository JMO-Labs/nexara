/**
 * @file tests/unit/bookmarks/BookmarksPage.test.tsx
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/lib/api/bookmarks", () => ({
  toggleBookmark: vi.fn(),
  listBookmarks: vi.fn(),
}));
vi.mock("@/components/feed/PostCard", () => ({
  PostCard: ({ post }: { post: { id: string } }) => (
    <div data-testid="post">{post.id}</div>
  ),
}));
import * as api from "@/lib/api/bookmarks";
import BookmarksPage from "@/app/app/bookmarks/page";

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <BookmarksPage />
    </QueryClientProvider>,
  );
}
const bm = (id: string) => ({
  id: `b${id}`,
  bookmarked_at: "2026-01-01T00:00:00Z",
  post: { id },
});

beforeEach(() => vi.resetAllMocks());

describe("BookmarksPage", () => {
  it("shows empty state", async () => {
    vi.mocked(api.listBookmarks).mockResolvedValue({
      bookmarks: [],
      pagination: { cursor: null, has_more: false },
    } as never);
    wrap();
    expect(await screen.findByText(/No bookmarks yet/)).toBeInTheDocument();
  });

  it("lists and loads more", async () => {
    vi.mocked(api.listBookmarks)
      .mockResolvedValueOnce({
        bookmarks: [bm("1")],
        pagination: { cursor: "c1", has_more: true },
      } as never)
      .mockResolvedValueOnce({
        bookmarks: [bm("2")],
        pagination: { cursor: null, has_more: false },
      } as never);
    wrap();
    expect(await screen.findAllByTestId("post")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: /load more/i }));
    await waitFor(() => expect(screen.getAllByTestId("post")).toHaveLength(2));
    expect(api.listBookmarks).toHaveBeenLastCalledWith("c1", 20);
  });
});
