/**
 * @file tests/unit/prompts/PromptResponsesPage.test.tsx
 * @brief Prompt responses page states, load more, and card link.
 */
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Suspense } from "react";
import PromptResponsesPage from "@/app/app/prompts/[id]/page";

const st = vi.hoisted(() => ({
  prompt: {} as Record<string, unknown>,
  resp: {} as Record<string, unknown>,
  fetchNext: vi.fn(),
}));
vi.mock("@/hooks/usePrompts", () => ({ usePromptPost: () => st.prompt }));
vi.mock("@/hooks/usePromptResponses", () => ({
  useInfinitePromptResponses: () => st.resp,
  usePromptResponses: () => ({ data: { response_count: 2 } }),
}));
vi.mock("@/components/feed/PostCard", () => ({
  PostCard: ({ post }: { post: { id: string } }) => (
    <div data-testid="post-card">{post.id}</div>
  ),
}));

async function setup() {
  const params = Promise.resolve({ id: "pp1" });
  await act(async () => {
    render(
      <Suspense fallback={null}>
        <PromptResponsesPage params={params} />
      </Suspense>,
    );
    await params;
  });
}

const page = (ids: string[], next: string | null) => ({
  response_count: ids.length,
  items: ids.map((id) => ({ id })),
  next_cursor: next,
});

describe("PromptResponsesPage", () => {
  beforeEach(() => {
    st.fetchNext = vi.fn();
    st.prompt = { data: { prompt: { title: "Favorite tradition?" } } };
  });

  it("shows title and response posts", async () => {
    st.resp = {
      data: { pages: [page(["a", "b"], null)] },
      hasNextPage: false,
      fetchNextPage: st.fetchNext,
    };
    await setup();
    expect(screen.getByText("Favorite tradition?")).toBeInTheDocument();
    expect(screen.getAllByTestId("post-card")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /load more/i })).toBeNull();
  });

  it("loads more via next_cursor", async () => {
    st.resp = {
      data: { pages: [page(["a"], "c1")] },
      hasNextPage: true,
      fetchNextPage: st.fetchNext,
    };
    await setup();
    await userEvent.click(screen.getByRole("button", { name: /load more/i }));
    expect(st.fetchNext).toHaveBeenCalled();
  });

  it("shows empty state", async () => {
    st.resp = { data: { pages: [page([], null)] }, hasNextPage: false };
    await setup();
    expect(screen.getByText(/no responses yet/i)).toBeInTheDocument();
  });

  it("shows loading status", async () => {
    st.resp = { isLoading: true };
    await setup();
    expect(
      screen.getByRole("status", { name: /loading responses/i }),
    ).toBeInTheDocument();
  });

  it("shows error with retry", async () => {
    const refetch = vi.fn();
    st.resp = { isError: true, refetch };
    await setup();
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });
});
