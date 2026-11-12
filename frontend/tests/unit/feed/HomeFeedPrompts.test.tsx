/**
 * @file tests/unit/feed/HomeFeedPrompts.test.tsx
 * @brief HomeFeed active-prompt section and reply-to-composer wiring.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";

const state = vi.hoisted(() => ({
  prompts: [] as unknown[],
  composer: vi.fn(),
}));
vi.mock("@/hooks/useActivePrompts", () => ({
  useActivePrompts: () => ({ data: state.prompts }),
}));
vi.mock("@/hooks/usePromptResponses", () => ({
  usePromptResponses: () => ({ data: undefined }),
}));
vi.mock("@/components/prompts/PromptResponseModal", () => ({
  PromptResponseModal: () => null,
}));
vi.mock("@/hooks/useHomeFeed", () => ({
  useHomeFeed: () => ({
    items: [],
    pending: [],
    freshIds: new Set<string>(),
    reveal: vi.fn(),
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isLoading: false,
  }),
}));
vi.mock("@/components/feed/PostComposer", () => ({
  PostComposer: (props: Record<string, unknown>) => {
    state.composer(props);
    return <div data-testid="composer" />;
  },
}));

import { HomeFeed } from "@/components/home/HomeFeed";

const pp = (id: string, promptId: string, title: string) => ({
  id,
  post_id: "x" + id,
  prompt: {
    id: promptId,
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

describe("HomeFeed prompts", () => {
  beforeEach(() => {
    state.composer.mockClear();
    window.scrollTo = vi.fn() as unknown as typeof window.scrollTo;
  });

  it("renders nothing for prompts when list is empty", () => {
    state.prompts = [];
    render(<HomeFeed />);
    expect(
      screen.queryByRole("region", { name: /active prompts/i }),
    ).not.toBeInTheDocument();
  });

  it("renders one card per active prompt", () => {
    state.prompts = [pp("a", "pa", "Q one"), pp("b", "pb", "Q two")];
    render(<HomeFeed />);
    const region = screen.getByRole("region", { name: /active prompts/i });
    expect(
      within(region).getAllByRole("button", { name: /respond/i }),
    ).toHaveLength(2);
    expect(screen.getByText("Q two")).toBeInTheDocument();
  });

  it("Respond opens composer with prompt post id and title", async () => {
    state.prompts = [pp("a", "pa", "Q one")];
    render(<HomeFeed />);
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: /respond/i }));
    expect(state.composer).toHaveBeenLastCalledWith(
      expect.objectContaining({
        replyToPromptId: "a",
        replyToPromptTitle: "Q one",
      }),
    );
  });
});
