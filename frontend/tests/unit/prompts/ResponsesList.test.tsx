/**
 * @file tests/unit/prompts/ResponsesList.test.tsx
 * @brief Client-side search over loaded responses.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { PromptResponsesList } from "@/components/prompts/PromptResponsesList";

vi.mock("@/hooks/usePromptResponses", () => ({
  useInfinitePromptResponses: () => ({
    data: {
      pages: [
        {
          items: [
            { id: "a", content: "Pancakes on Sunday" },
            { id: "b", content: "Caroling" },
          ],
        },
      ],
    },
    hasNextPage: false,
  }),
}));
vi.mock("@/components/feed/PostCard", () => ({
  PostCard: ({ post }: { post: { id: string } }) => (
    <div data-testid="post-card">{post.id}</div>
  ),
}));

describe("PromptResponsesList search", () => {
  it("filters loaded responses by text", async () => {
    render(<PromptResponsesList promptPostId="p1" />);
    expect(screen.getAllByTestId("post-card")).toHaveLength(2);
    await userEvent.type(
      screen.getByRole("searchbox", { name: /search responses/i }),
      "carol",
    );
    expect(screen.getAllByTestId("post-card")).toHaveLength(1);
    expect(screen.getByText("b")).toBeInTheDocument();
  });
});
