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
let isError = false;
const refetch = vi.fn();
vi.mock("@/hooks/usePosts", () => ({
  useComments: () => ({
    data: { pages: [{ items }] },
    isLoading: false,
    isError,
    refetch,
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
    expect(
      screen.getByRole("heading", { name: "No comments yet" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Start the conversation.")).toBeInTheDocument();
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

  it("shows error with retry instead of empty state", async () => {
    items = [];
    isError = true;
    const user = userEvent.setup();
    render(<CommentThread postId="p1" />);
    expect(screen.queryByText("No comments yet")).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/couldn.t load/i);
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
    isError = false;
  });

  it("offers Report on each comment", () => {
    items = [
      {
        id: "c9",
        content: "x",
        created_at: new Date().toISOString(),
        author: { id: "u2", display_name: "Bob", avatar_url: null },
        replies: [],
      },
    ];
    render(<CommentThread postId="p1" />);
    expect(screen.getByRole("button", { name: "Report" })).toBeInTheDocument();
  });
});

describe("CommentThread brand styling", () => {
  it("renders a glass composer row with a borderless textarea", () => {
    items = [];
    render(<CommentThread postId="p1" />);
    const field = screen.getByPlaceholderText("Add a comment…");
    expect(field.parentElement).toHaveClass("glass-item", "rounded-full");
    expect(field.className).toContain("resize-none");
    expect(field.className).not.toContain("border-current");
  });

  it("uses glass-item bubbles and no hard dividers on the list", () => {
    items = [
      {
        id: "c1",
        content: "nice",
        created_at: new Date().toISOString(),
        author: { id: "u2", display_name: "Bob", avatar_url: null },
        replies: [],
      },
    ];
    const { container } = render(<CommentThread postId="p1" />);
    const bubble = screen.getByText("Bob").parentElement as HTMLElement;
    expect(bubble).toHaveClass("glass-item", "rounded-[20px]");
    expect(container.innerHTML).not.toContain("border-y");
  });
});
