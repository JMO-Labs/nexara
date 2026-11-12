/**
 * @file tests/unit/feed/CommentThread.test.tsx
 * @brief CommentThread empty state, list, and send.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CommentThread } from "@/components/feed/CommentThread";

const mutateAsync = vi.fn().mockResolvedValue({});
let items: unknown[] = [];
vi.mock("@/hooks/usePosts", () => ({
  useComments: () => ({
    data: { pages: [{ items }] },
    isLoading: false,
    hasNextPage: false,
    fetchNextPage: vi.fn(),
    isFetchingNextPage: false,
  }),
  useCreateComment: () => ({ mutateAsync, isPending: false }),
}));

describe("CommentThread", () => {
  it("shows empty state", () => {
    items = [];
    render(<CommentThread postId="p1" />);
    expect(screen.getByText("Be first to comment")).toBeInTheDocument();
  });

  it("renders comments and sends a new one", async () => {
    items = [
      {
        id: "c1",
        content: "nice",
        created_at: new Date().toISOString(),
        author: { id: "u2", display_name: "Bob", avatar_url: null },
        replies: [],
      },
    ];
    const user = userEvent.setup();
    render(<CommentThread postId="p1" />);
    expect(screen.getByText("Bob")).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText("Add a comment…"), "hi");
    await user.click(screen.getByRole("button", { name: "Send" }));
    expect(mutateAsync).toHaveBeenCalledWith({
      content: "hi",
      parent_id: undefined,
    });
  });
});
