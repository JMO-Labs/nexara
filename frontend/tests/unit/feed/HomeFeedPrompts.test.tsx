/**
 * @file tests/unit/feed/HomeFeedPrompts.test.tsx
 * @brief HomeFeed active-prompt section and reply-to-prompt composer wiring.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

const state = vi.hoisted(() => ({ prompts: [] as unknown[] }));
vi.mock("@/hooks/useActivePrompts", () => ({
  useActivePrompts: () => ({ data: state.prompts }),
}));
vi.mock("@/hooks/usePromptResponses", () => ({
  usePromptResponses: () => ({ data: undefined }),
}));
vi.mock("@/hooks/useHomeFeed", () => ({
  useHomeFeed: () => ({
    items: [{ kind: "post", id: "1", created_at: "t", post: { id: "1" } }],
    pending: [],
    freshIds: new Set<string>(),
    reveal: vi.fn(),
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isLoading: false,
  }),
}));
vi.mock("@/components/feed/PostCard", () => ({
  PostCard: () => <div>regular post</div>,
}));
vi.mock("@/components/feed/PostComposer", () => ({
  PostComposer: (p: {
    replyToPromptId?: string;
    replyToPromptTitle?: string;
  }) => (
    <div data-testid="composer">
      {p.replyToPromptId ?? "none"}|{p.replyToPromptTitle ?? ""}
    </div>
  ),
}));

import { HomeFeed } from "@/components/home/HomeFeed";

const pp = (id: string, title: string) => ({
  id,
  post_id: `post-${id}`,
  prompt: {
    id: `prompt-${id}`,
    title,
    body: "",
    prompt_type: "standard",
    interest_category_slug: null,
    interest_capture_hint: null,
  },
  response_count: 0,
  is_pinned: false,
  subgroup_id: null,
  subgroup_name: null,
  fired_at: "t",
  expires_at: "t",
});

beforeEach(() => {
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      observe() {}
      disconnect() {}
      unobserve() {}
    },
  );
  state.prompts = [pp("a", "Question A"), pp("b", "Question B")];
});

describe("HomeFeed prompts", () => {
  it("renders one card per active prompt above regular posts", () => {
    render(<HomeFeed />);
    const q = screen.getByText("Question A");
    const post = screen.getByText("regular post");
    expect(screen.getByText("Question B")).toBeInTheDocument();
    expect(
      q.compareDocumentPosition(post) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("renders no prompt section when list is empty", () => {
    state.prompts = [];
    render(<HomeFeed />);
    expect(screen.queryByLabelText("Active prompts")).toBeNull();
  });

  it("Reply passes prompt post id and title to the composer", () => {
    render(<HomeFeed />);
    expect(screen.getByTestId("composer")).toHaveTextContent("none|");
    fireEvent.click(
      screen.getByRole("button", { name: "Reply to: Question B" }),
    );
    expect(screen.getByTestId("composer")).toHaveTextContent("b|Question B");
  });
});
