/**
 * @file Trivia.test.tsx
 * @brief Tests for the example-trivia plugin UI (widget, leaderboard, stats).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const hooks = vi.hoisted(() => ({
  useTodayQuestion: vi.fn(),
  useSubmitAnswer: vi.fn(),
  useLeaderboard: vi.fn(),
  useMyStats: vi.fn(),
}));
vi.mock("@/plugins/example-trivia/hooks/useTrivia", () => hooks);
vi.mock("@/plugins/example-trivia/hooks/useTriviaWebSocket", () => ({
  useTriviaWebSocket: vi.fn(),
}));
vi.mock("@/lib/api/client", () => ({ apiGet: vi.fn(), apiPost: vi.fn() }));

import { useToasts } from "@/stores/toasts";
import { useSession } from "@/stores/session";
import { PluginRegistry } from "@/lib/plugins/plugin-loader";
import { PluginSlot } from "@/components/plugins/PluginSlot";
import registerDefault, {
  registerPlugin,
  TriviaWidget as LazyWidget,
} from "@/plugins/example-trivia";
import { TriviaWidget } from "@/plugins/example-trivia/components/TriviaWidget";
import { TriviaLeaderboard } from "@/plugins/example-trivia/components/TriviaLeaderboard";
import { StatsDetail } from "@/plugins/example-trivia/components/StatsDetail";

const manifest = {
  id: "example-trivia",
  name: "Trivia",
  version: "1.0.0",
  is_enabled: true,
  description: "",
};

const question = {
  question_id: "q1",
  text: "What is the capital of France?",
  options: [
    { id: "a", text: "Berlin" },
    { id: "b", text: "Paris" },
    { id: "c", text: "Rome" },
    { id: "d", text: "Madrid" },
  ],
  answered_today: false,
  streak: 3,
};

const stats = {
  rank: 2,
  streak: 3,
  best_streak: 7,
  total_correct: 30,
  total_answers: 40,
  percentage_correct: 75,
  days_participated: 40,
  first_answer_at: "2026-01-01",
  last_answer_at: "2026-11-11",
};

const entries = Array.from({ length: 25 }, (_, i) => ({
  rank: i + 1,
  user_id: `u${i + 1}`,
  user_name: `User ${i + 1}`,
  streak: 30 - i,
  total_correct: 100 - i,
}));

const mutate = vi.fn();

function q<T>(
  over: Partial<{ data: T; isLoading: boolean; isError: boolean }>,
) {
  return {
    data: undefined,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
    ...over,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  useToasts.getState().clear();
  useSession.setState({ user: { id: "u2" } as never });
  hooks.useTodayQuestion.mockReturnValue(q({ data: question }));
  hooks.useSubmitAnswer.mockReturnValue({ mutate, isPending: false });
  hooks.useLeaderboard.mockReturnValue(
    q({ data: { entries, total_count: 100, pages: 4 } }),
  );
  hooks.useMyStats.mockReturnValue(q({ data: stats }));
});

const renderWidget = () =>
  render(<TriviaWidget pluginId="example-trivia" pluginManifest={manifest} />);

describe("TriviaWidget", () => {
  it("renders question, streak and 4 labelled options", () => {
    renderWidget();
    expect(screen.getByText(question.text)).toBeInTheDocument();
    expect(screen.getByText(/3-day streak/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Option A: Berlin" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Option D: Madrid" }),
    ).toBeInTheDocument();
  });

  it("disables submit until an option is selected, then submits", async () => {
    const user = userEvent.setup();
    renderWidget();
    const submit = screen.getByRole("button", { name: /submit/i });
    expect(submit).toBeDisabled();
    const b = screen.getByRole("button", { name: "Option B: Paris" });
    await user.click(b);
    expect(b).toHaveAttribute("aria-pressed", "true");
    await user.click(submit);
    expect(mutate).toHaveBeenCalledWith(
      { question_id: "q1", answer_id: "b" },
      expect.any(Object),
    );
  });

  it("supports keyboard selection and Enter to submit", async () => {
    const user = userEvent.setup();
    renderWidget();
    await user.tab();
    expect(
      screen.getByRole("button", { name: "Option A: Berlin" }),
    ).toHaveFocus();
    await user.keyboard(" ");
    await user.keyboard("{Enter}");
    expect(mutate).toHaveBeenCalledWith(
      { question_id: "q1", answer_id: "a" },
      expect.any(Object),
    );
  });

  it("shows correct toast and locks options on success", async () => {
    mutate.mockImplementation((_v, o) =>
      o.onSuccess({ correct: true, streak: 4 }),
    );
    const user = userEvent.setup();
    renderWidget();
    await user.click(screen.getByRole("button", { name: "Option B: Paris" }));
    await user.click(screen.getByRole("button", { name: /submit/i }));
    expect(useToasts.getState().items[0]).toMatchObject({
      variant: "success",
      message: "Correct! +1 streak",
    });
    expect(
      screen.getByRole("button", { name: "Option A: Berlin" }),
    ).toBeDisabled();
  });

  it("shows incorrect toast", async () => {
    mutate.mockImplementation((_v, o) =>
      o.onSuccess({ correct: false, streak: 0 }),
    );
    const user = userEvent.setup();
    renderWidget();
    await user.click(screen.getByRole("button", { name: "Option C: Rome" }));
    await user.click(screen.getByRole("button", { name: /submit/i }));
    expect(useToasts.getState().items[0]).toMatchObject({
      variant: "danger",
      message: "Incorrect",
    });
  });

  it("shows a friendly toast when submission fails", async () => {
    mutate.mockImplementation((_v, o) => o.onError(new Error("500 boom")));
    const user = userEvent.setup();
    renderWidget();
    await user.click(screen.getByRole("button", { name: "Option C: Rome" }));
    await user.click(screen.getByRole("button", { name: /submit/i }));
    const t = useToasts.getState().items[0];
    expect(t.variant).toBe("danger");
    expect(t.message).not.toMatch(/boom/);
  });

  it("marks submission busy while pending", () => {
    hooks.useSubmitAnswer.mockReturnValue({ mutate, isPending: true });
    renderWidget();
    expect(
      screen.getByRole("group", { name: /answer options/i }),
    ).toHaveAttribute("aria-busy", "true");
  });

  it("shows already-answered state with chosen answer", () => {
    hooks.useTodayQuestion.mockReturnValue(
      q({ data: { ...question, answered_today: true, user_answer_id: "b" } }),
    );
    renderWidget();
    expect(screen.getByText(/already answered today/i)).toBeInTheDocument();
    expect(screen.getByText(/Paris/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /submit/i })).toBeNull();
    expect(
      screen.getByRole("button", { name: /view leaderboard/i }),
    ).toBeInTheDocument();
  });

  it("shows loading state", () => {
    hooks.useTodayQuestion.mockReturnValue(q({ isLoading: true }));
    renderWidget();
    expect(
      screen.getByRole("status", { name: /loading trivia/i }),
    ).toBeInTheDocument();
  });

  it("shows error state with toast and retry", async () => {
    const refetch = vi.fn();
    hooks.useTodayQuestion.mockReturnValue({
      ...q({ isError: true }),
      refetch,
    });
    const user = userEvent.setup();
    renderWidget();
    expect(screen.getByRole("alert")).toHaveTextContent(/couldn.t load/i);
    expect(useToasts.getState().items[0].variant).toBe("danger");
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });

  it("opens and closes the leaderboard modal", async () => {
    const user = userEvent.setup();
    renderWidget();
    await user.click(screen.getByRole("button", { name: /view leaderboard/i }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});

describe("TriviaLeaderboard", () => {
  const renderLb = (onClose = vi.fn()) =>
    render(<TriviaLeaderboard open onClose={onClose} />);

  it("renders table and highlights current user", () => {
    renderLb();
    const table = screen.getByRole("table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((c) => c.textContent),
    ).toEqual(["Rank", "User Name", "Current Streak", "Total Correct"]);
    const me = screen.getByText("User 2").closest("tr");
    expect(me).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("User 1").closest("tr")).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("paginates with Next/Previous", async () => {
    const user = userEvent.setup();
    renderLb();
    expect(hooks.useLeaderboard).toHaveBeenLastCalledWith(1);
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(hooks.useLeaderboard).toHaveBeenLastCalledWith(2);
    expect(screen.getByText(/page 2 of 4/i)).toBeInTheDocument();
  });

  it("shows my detailed stats", async () => {
    const user = userEvent.setup();
    renderLb();
    await user.click(
      screen.getByRole("button", { name: /view my detailed stats/i }),
    );
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("closes via close button", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderLb(onClose);
    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it("shows friendly error", () => {
    hooks.useLeaderboard.mockReturnValue(q({ isError: true }));
    renderLb();
    expect(screen.getByRole("alert")).toHaveTextContent(
      /couldn.t load the leaderboard/i,
    );
  });
});

describe("StatsDetail", () => {
  it("displays all stats", () => {
    render(<StatsDetail />);
    expect(screen.getByText("#2")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();
    expect(screen.getByText("40 answers")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("copies leaderboard link on share", async () => {
    const user = userEvent.setup();
    const writeText = vi
      .spyOn(navigator.clipboard, "writeText")
      .mockResolvedValue();
    render(<StatsDetail />);
    await user.click(screen.getByRole("button", { name: /share/i }));
    expect(writeText).toHaveBeenCalledWith(
      expect.stringContaining("trivia=leaderboard"),
    );
  });
});

describe("registerPlugin", () => {
  beforeEach(() => PluginRegistry.getInstance().reset());

  it("registers widget in sidebar-widget slot (named and default export)", () => {
    expect(registerDefault).toBe(registerPlugin);
    registerPlugin(PluginRegistry.getInstance());
    const entries =
      PluginRegistry.getInstance().getSlotComponents("sidebar-widget");
    expect(entries).toEqual([
      { pluginId: "example-trivia", component: LazyWidget },
    ]);
  });

  it("loads in the sidebar-widget slot", async () => {
    registerPlugin(PluginRegistry.getInstance());
    render(<PluginSlot slotName="sidebar-widget" />);
    expect(await screen.findByText(question.text)).toBeInTheDocument();
  });
});
