/**
 * @file tests/unit/post/PostPage.test.tsx
 * @brief Post detail page states.
 */
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    expect(
      screen.getByRole("heading", { level: 1, name: "Post" }),
    ).toBeInTheDocument();
    expect(screen.getByText("comments").closest(".glass")).not.toBeNull();
  });
  it("shows not found when no post and no error", async () => {
    state.v = {};
    await setup();
    expect(screen.getByText("Post not found")).toBeInTheDocument();
  });
  it("shows loading skeleton status", async () => {
    state.v = { isLoading: true };
    await setup();
    expect(
      screen.getByRole("status", { name: /loading post/i }),
    ).toBeInTheDocument();
  });
  it("shows error with retry", async () => {
    const refetch = vi.fn();
    state.v = { isError: true, refetch };
    await setup();
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });
  it("uses the full frame width with top padding clearing the TopBar", async () => {
    state.v = { data: { id: "1" } };
    await setup();
    const root = screen.getByText("post-card").closest("div.mx-auto");
    expect(root).not.toBeNull();
    expect(root).toHaveClass("w-full", "flex-col", "pt-4", "md:pt-6");
    expect(root!.className).not.toContain("max-w-3xl");
    expect(root!.className).not.toMatch(/\bgrid|\bmd:flex-row|\bcols-/);
  });
});
