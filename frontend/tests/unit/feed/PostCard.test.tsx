/**
 * @file tests/unit/feed/PostCard.test.tsx
 * @brief PostCard prompt summary badge and reply-to-prompt label tests.
 */
import { vi, describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import type { Post } from "@/lib/api/posts";

vi.mock("@/stores/session", () => ({
  useSession: vi.fn((selector) =>
    selector({ user: { id: "u1", role: "member" } }),
  ),
}));
vi.mock("@/stores/confirmDialog", () => ({
  useConfirmDialog: vi.fn((selector) => selector({ confirm: vi.fn() })),
}));
vi.mock("@/hooks/usePosts", () => ({
  useDeletePost: () => ({ mutate: vi.fn() }),
  useTogglePostReaction: () => ({ mutate: vi.fn() }),
}));
vi.mock("@/components/feed/PostHeader", () => ({ PostHeader: () => <div /> }));
vi.mock("@/components/feed/CommentThread", () => ({
  CommentThread: () => <div />,
}));

import { PostCard } from "@/components/feed/PostCard";

function makePost(overrides: Partial<Post> = {}): Post {
  return {
    id: "p1",
    content: "Hello",
    author: { id: "u2", display_name: "Ann" },
    media: [],
    reactions: [],
    comment_count: 0,
    ...overrides,
  } as unknown as Post;
}

describe("PostCard prompt markers", () => {
  it("shows Prompt summary badge for summary posts", () => {
    render(<PostCard post={makePost({ is_prompt_summary: true })} />);
    expect(screen.getByText("Prompt summary")).toBeInTheDocument();
  });

  it("links reply label to the prompt", () => {
    render(<PostCard post={makePost({ reply_to_prompt_id: "pr9" })} />);
    const link = screen.getByRole("link", { name: "Reply to a prompt" });
    expect(link).toHaveAttribute("href", "/app/prompts/pr9");
  });

  it("shows neither for normal posts", () => {
    render(<PostCard post={makePost()} />);
    expect(screen.queryByText("Prompt summary")).toBeNull();
    expect(screen.queryByText("Reply to a prompt")).toBeNull();
  });
});
