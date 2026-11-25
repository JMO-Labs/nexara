/**
 * @file tests/unit/prompts/DailyQuestionStack.test.tsx
 * @brief Questions-of-the-day stack: rows, expand, expand-all, quick nav,
 *        timeline placement helper.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("@/hooks/usePromptResponses", () => ({
  useInfinitePromptResponses: (id: string) => ({
    data: {
      pages: [
        { answered: id === "b", count: 3, locked: id !== "b", items: [] },
      ],
    },
  }),
}));
vi.mock("@/components/prompts/DailyQuestionCard", () => ({
  DailyQuestionCard: ({ post }: { post: { id: string } }) => (
    <textarea aria-label={`answer-${post.id}`} />
  ),
}));

import { DailyQuestionStack } from "@/components/prompts/DailyQuestionStack";
import { dayLabel, stackIndex } from "@/components/prompts/stackPlacement";
import { openFirstUnanswered, useQotd } from "@/stores/qotd";
import type { PromptPost } from "@/lib/api/prompts";

const post = (id: string, body: string, fired: string): PromptPost => ({
  id,
  post_id: `x${id}`,
  prompt: {
    id: `pr${id}`,
    title: body,
    body,
    prompt_type: "daily_question",
    interest_category_slug: null,
    interest_capture_hint: null,
  },
  response_count: 3,
  is_pinned: false,
  subgroup_id: null,
  subgroup_name: id === "c" ? "Cousins" : null,
  fired_at: fired,
  expires_at: "2099-01-01",
});
const now = new Date().toISOString();
const posts = [
  post("a", "Old one?", "2020-01-01T10:00:00Z"),
  post("b", "Answered one?", now),
  post("c", "Group one?", "2021-01-01T10:00:00Z"),
];

beforeEach(() => useQotd.setState({ answered: {}, ids: null }));

describe("DailyQuestionStack", () => {
  it("collapsed: one row per question with status", () => {
    render(<DailyQuestionStack posts={posts} />);
    const rows = screen.getAllByRole("button", { expanded: false });
    expect(rows.filter((r) => r.hasAttribute("aria-controls"))).toHaveLength(3);
    expect(screen.getByText(/Answered · 3 answers/)).toBeInTheDocument();
    expect(screen.getAllByText("Answer")).toHaveLength(2);
    expect(screen.getByText(/Cousins/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^answer-/)).toBeNull();
  });

  it("click expands only that row; expand all toggles", async () => {
    const u = userEvent.setup();
    render(<DailyQuestionStack posts={posts} />);
    await u.click(screen.getByRole("button", { name: /Old one/ }));
    expect(screen.getByLabelText("answer-a")).toBeInTheDocument();
    expect(screen.queryByLabelText("answer-b")).toBeNull();
    await u.click(screen.getByRole("button", { name: "Expand all" }));
    expect(screen.getAllByLabelText(/^answer-/)).toHaveLength(3);
    await u.click(screen.getByRole("button", { name: "Collapse all" }));
    expect(screen.queryByLabelText(/^answer-/)).toBeNull();
  });

  it("quick-nav opens and focuses first unanswered", () => {
    render(<DailyQuestionStack posts={posts} />);
    act(() => openFirstUnanswered());
    // newest-first order: b (answered) then c, then a -> c is first unanswered
    expect(screen.getByLabelText("answer-c")).toHaveFocus();
    expect(screen.queryByLabelText("answer-a")).toBeNull();
  });

  it("quick-nav scrolls only the feed card, never the page", () => {
    const { container } = render(
      <div data-testid="pane" style={{ overflowY: "auto" }}>
        <DailyQuestionStack posts={posts} />
      </div>,
    );
    const pane = container.firstElementChild as HTMLElement;
    Object.defineProperty(pane, "scrollHeight", { value: 2000 });
    Object.defineProperty(pane, "clientHeight", { value: 500 });
    pane.scrollTo = vi.fn();
    const intoView = vi
      .spyOn(Element.prototype, "scrollIntoView")
      .mockImplementation(() => {});
    act(() => openFirstUnanswered());
    expect(pane.scrollTo).toHaveBeenCalled();
    expect(intoView).not.toHaveBeenCalled();
    intoView.mockRestore();
  });
});

describe("placement", () => {
  const items = [
    { created_at: "2026-01-03T00:00:00Z" },
    { created_at: "2026-01-01T00:00:00Z" },
  ];
  it("inserts before first older item", () => {
    expect(stackIndex(items, "2026-01-02T00:00:00Z")).toBe(1);
    expect(stackIndex(items, "2026-01-04T00:00:00Z")).toBe(0);
  });
  it("end when all newer, 0 when empty", () => {
    expect(stackIndex(items, "2025-01-01T00:00:00Z")).toBe(2);
    expect(stackIndex([], "2025-01-01T00:00:00Z")).toBe(0);
  });
  it("day labels", () => {
    const n = new Date(2026, 5, 10, 12);
    expect(dayLabel(new Date(2026, 5, 10, 1).toISOString(), n)).toBe("Today");
    expect(dayLabel(new Date(2026, 5, 9, 23).toISOString(), n)).toBe(
      "Yesterday",
    );
  });
});
