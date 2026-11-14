/**
 * @file tests/unit/feed/PostHeader.test.tsx
 * @brief PostHeader identity and owner menu.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PostHeader } from "@/components/feed/PostHeader";
import type { Post } from "@/lib/api/posts";
import { TooltipProvider } from "@/components/ui/Tooltip";

const post = {
  id: "p1",
  author: {
    id: "u1",
    username: "alice",
    display_name: "Alice",
    avatar_url: null,
  },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
} as unknown as Post;

describe("PostHeader", () => {
  it("shows author and a Report-only menu for non-owners", async () => {
    const user = userEvent.setup();
    render(<PostHeader post={post} isAuthor={false} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Post options" }));
    expect(
      await screen.findByRole("menuitem", { name: "Report" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: "Delete" })).toBeNull();
  });

  it("hides Report for the author", async () => {
    const user = userEvent.setup();
    render(<PostHeader post={post} isAuthor onDelete={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Post options" }));
    expect(screen.queryByRole("menuitem", { name: "Report" })).toBeNull();
  });

  it("author menu fires onDelete", async () => {
    const onDelete = vi.fn();
    const user = userEvent.setup();
    render(<PostHeader post={post} isAuthor onDelete={onDelete} />);
    await user.click(screen.getByRole("button", { name: "Post options" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalled();
  });

  it("shows a Post options tooltip on keyboard focus", async () => {
    render(
      <TooltipProvider>
        <PostHeader post={post} isAuthor onDelete={vi.fn()} />
      </TooltipProvider>,
    );
    await userEvent.tab();
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Post options",
    );
  });
});
