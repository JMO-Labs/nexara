/**
 * @file tests/unit/post/PostPage.test.tsx
 * @brief Post detail page states.
 */
import { act, render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Suspense } from "react";
import PostPage from "@/app/app/post/[id]/page";

const state = vi.hoisted(() => ({ v: {} as Record<string, unknown> }));
vi.mock("@/hooks/usePosts", () => ({ usePost: () => state.v }));
vi.mock("@/components/feed/PostCard", () => ({
  PostCard: () => <div>post-card</div>,
}));
vi.mock("@/components/feed/CommentThread", () => ({
  CommentThread: () => <div>comments</div>,
}));

async function setup() {
  const params = Promise.resolve({ id: "1" });
  await act(async () => {
    render(
      <Suspense fallback={null}>
        <PostPage params={params} />
      </Suspense>,
    );
    await params;
  });
  return screen.findByRole("link", { name: /back to feed/i });
}

describe("PostPage", () => {
  it("renders post, comments and back link", async () => {
    state.v = { data: { id: "1" } };
    const link = await setup();
    expect(link).toHaveAttribute("href", "/app");
    expect(screen.getByText("post-card")).toBeInTheDocument();
    expect(screen.getByText("comments")).toBeInTheDocument();
  });
  it("shows not found on error", async () => {
    state.v = { isError: true };
    await setup();
    expect(screen.getByText("Post not found")).toBeInTheDocument();
  });
});
