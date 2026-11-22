/**
 * @file tests/unit/components/prompts/DailyQuestionCard.test.tsx
 * @brief Locked state shows the count (not answers); unlocked renders answers.
 */
import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { PromptPost } from "@/lib/api/prompts";

const st = vi.hoisted(() => ({
  page: {} as Record<string, unknown>,
  feature: true,
}));
vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));
vi.mock("@/hooks/useFeature", () => ({ useFeature: () => st.feature }));
vi.mock("@/components/prompts/SuggestQuestionDialog", () => ({
  SuggestQuestionDialog: () => null,
}));
vi.mock("@/hooks/usePosts", () => ({
  useCreatePost: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock("@/hooks/usePromptResponses", () => ({
  useInfinitePromptResponses: () => ({ data: { pages: [st.page] } }),
}));
vi.mock("@/components/prompts/PromptResponsesList", () => ({
  PromptResponsesList: () => <div>ANSWERS LIST</div>,
}));

import { DailyQuestionCard } from "@/components/prompts/DailyQuestionCard";

const post = {
  id: "pp1",
  response_count: 5,
  prompt: { title: "Daily question", body: "Best meal ever?" },
} as unknown as PromptPost;

beforeEach(() => {
  st.feature = true;
});

describe("DailyQuestionCard", () => {
  it("locked: shows count text and no answers", () => {
    st.page = { locked: true, count: 2, items: [] };
    render(<DailyQuestionCard post={post} />);
    expect(screen.getByText("Best meal ever?")).toBeTruthy();
    expect(screen.getByText(/Answer to see what everyone said/)).toBeTruthy();
    expect(screen.getByText(/2 answers/)).toBeTruthy();
    expect(screen.queryByText("ANSWERS LIST")).toBeNull();
    expect(screen.getByLabelText("Your answer")).toBeTruthy();
  });

  it("unlocked: renders answers, no lock text", () => {
    st.page = { items: [{ id: "a" }] };
    render(<DailyQuestionCard post={post} />);
    expect(screen.getByText("ANSWERS LIST")).toBeTruthy();
    expect(screen.queryByText(/Answer to see/)).toBeNull();
  });

  it("renders nothing when the feature is off", () => {
    st.feature = false;
    st.page = {};
    const { container } = render(<DailyQuestionCard post={post} />);
    expect(container.firstChild).toBeNull();
  });
});
