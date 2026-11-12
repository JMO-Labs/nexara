/**
 * @file tests/unit/feed/PromptPostCard.test.tsx
 * @brief PromptPostCard component tests (render, reply callback, live refresh).
 */
// Mock the hook BEFORE importing the component
import { vi } from "vitest";

vi.mock("@/hooks/usePromptResponses", () => ({
  usePromptResponses: () => ({
    data: { response_count: 12 },
    isLoading: false,
  }),
}));

// Now safe to import component and dependencies
import { describe, it, expect } from "vitest";
import type React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { PromptPost } from "@/lib/api/prompts";
import { PromptPostCard } from "@/components/feed/PromptPostCard";

function createPromptPost(overrides?: Partial<PromptPost>): PromptPost {
  return {
    id: "p1",
    post_id: "post1",
    prompt: {
      id: "prompt1",
      title: "What is your favorite holiday tradition?",
      body: "Share a cherished memory",
      prompt_type: "standard",
      interest_category_slug: null,
      interest_capture_hint: null,
    },
    response_count: 12,
    is_pinned: true,
    subgroup_id: null,
    subgroup_name: null,
    fired_at: "2026-04-27",
    expires_at: "2026-04-29T23:59:59Z",
    ...overrides,
  };
}

describe("PromptPostCard", () => {
  function wrap(ui: React.ReactNode) {
    return render(ui);
  }

  it("renders prompt question and response count", () => {
    const post = createPromptPost();
    wrap(<PromptPostCard post={post} />);
    expect(screen.getByText(post.prompt.title)).toBeInTheDocument();
    expect(screen.getByText("12 responses")).toBeInTheDocument();
  });

  it("clicking Reply triggers onReply callback with prompt post id", async () => {
    const onReply = vi.fn();
    const post = createPromptPost();
    const user = userEvent.setup();
    wrap(<PromptPostCard post={post} onReply={onReply} />);
    const replyBtn = screen.getByRole("button", { name: /reply/i });
    await user.click(replyBtn);
    expect(onReply).toHaveBeenCalledWith(post.id);
  });

  it("renders aria-live region for response count updates", () => {
    const post = createPromptPost();
    wrap(<PromptPostCard post={post} />);
    const liveRegion = screen.getByRole("status");
    expect(liveRegion).toHaveAttribute("aria-live", "polite");
  });

  it("displays subgroup chip when subgroup_name is set", () => {
    const post = createPromptPost({ subgroup_name: "Book Club" });
    wrap(<PromptPostCard post={post} />);
    expect(screen.getByText("Book Club")).toBeInTheDocument();
  });

  it("renders pinned icon when is_pinned is true", () => {
    const post = createPromptPost({ is_pinned: true });
    wrap(<PromptPostCard post={post} />);
    const pinnedIndicator = screen.getByTestId("pinned-icon");
    expect(pinnedIndicator).toBeInTheDocument();
  });

  it("renders interest capture hint when prompt_type is interest_capture", () => {
    const post = createPromptPost({
      prompt: {
        id: "prompt2",
        title: "What cuisines do you love?",
        body: "Help us learn about your tastes",
        prompt_type: "interest_capture",
        interest_category_slug: "cooking",
        interest_capture_hint: "Pick your favorite cuisines",
      },
    });
    wrap(<PromptPostCard post={post} />);
    expect(
      screen.getByText(/Pick your favorite cuisines/i),
    ).toBeInTheDocument();
  });
});
