/**
 * @file tests/unit/feed/PostCard.test.tsx
 * @brief PostCard prompt badges: summary badge and reply-to-prompt label.
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import messages from "@/i18n/en-US.json";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { PostCard } from "@/components/feed/PostCard";
import type { Post } from "@/lib/api/posts";

vi.mock("next-intl", () => ({
  useTranslations: (ns: string) => (key: string) =>
    (messages as unknown as Record<string, Record<string, string>>)[ns]?.[
      key
    ] ?? key,
}));

vi.mock("@/hooks/usePosts", () => ({
  useDeletePost: () => ({ mutate: vi.fn() }),
  useTogglePostReaction: () => ({ mutate: vi.fn() }),
}));

function makePost(overrides: Partial<Post> = {}): Post {
  const now = new Date().toISOString();
  return {
    id: "p1",
    content: "Hello world",
    author: {
      id: "u1",
      username: "alice",
      display_name: "Alice",
      avatar_url: null,
    },
    media: [],
    poll: null,
    reactions: [],
    comment_count: 0,
    created_at: now,
    updated_at: now,
    subgroup_id: null,
    subgroup_name: null,
    subgroup_slug: null,
    ...overrides,
  };
}

describe("PostCard prompt badges", () => {
  it("shows a Prompt summary badge for summary posts", () => {
    renderWithProviders(
      <PostCard post={makePost({ is_prompt_summary: true })} />,
    );
    expect(screen.getByText("Prompt summary")).toBeInTheDocument();
  });

  it("shows a Reply to a prompt link for prompt replies", () => {
    renderWithProviders(
      <PostCard post={makePost({ reply_to_prompt_id: "pr-42" })} />,
    );
    const link = screen.getByRole("link", { name: "Reply to a prompt" });
    expect(link).toHaveAttribute("href", "/app/prompts/pr-42");
  });

  it("shows neither for normal posts", () => {
    renderWithProviders(
      <PostCard
        post={makePost({ is_prompt_summary: false, reply_to_prompt_id: null })}
      />,
    );
    expect(screen.queryByText("Prompt summary")).toBeNull();
    expect(screen.queryByText("Reply to a prompt")).toBeNull();
  });
});
