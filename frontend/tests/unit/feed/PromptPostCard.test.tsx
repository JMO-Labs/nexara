/**
 * @file tests/unit/feed/PromptPostCard.test.tsx
 * @brief PromptPostCard feed behaviour: reply callback and ARIA landmark.
 */
import { describe, it, expect, vi } from "vitest";

vi.mock("@/hooks/usePosts", () => ({
  useCreatePost: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock("@/hooks/usePromptResponses", () => ({
  usePromptResponses: () => ({
    data: { response_count: 3 },
    isLoading: false,
  }),
}));

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PromptPost } from "@/lib/api/prompts";
import { PromptPostCard } from "@/components/feed/PromptPostCard";

const post: PromptPost = {
  id: "p1",
  post_id: "post1",
  prompt: {
    id: "prompt1",
    title: "Favorite tradition?",
    body: "Share",
    prompt_type: "standard",
    interest_category_slug: null,
    interest_capture_hint: null,
  },
  response_count: 3,
  is_pinned: false,
  subgroup_id: null,
  subgroup_name: null,
  fired_at: "2026-04-27",
  expires_at: "2026-04-29T23:59:59Z",
};

describe("PromptPostCard (feed)", () => {
  it("exposes the card as a labelled article", () => {
    render(<PromptPostCard post={post} />);
    expect(
      screen.getByRole("article", { name: /prompt: favorite tradition/i }),
    ).toBeInTheDocument();
  });

  it("clicking Respond with onReply calls it instead of the modal", async () => {
    const onReply = vi.fn();
    const user = userEvent.setup();
    render(<PromptPostCard post={post} onReply={onReply} />);
    await user.click(screen.getByRole("button", { name: /respond/i }));
    expect(onReply).toHaveBeenCalledWith(post.id, post.prompt.title);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
