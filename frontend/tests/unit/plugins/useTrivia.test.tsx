/**
 * @file useTrivia.test.tsx
 * @brief Tests for example-trivia TanStack Query hooks (API contract).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

vi.mock("@/lib/api/client", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  seg: (v: string | number) => encodeURIComponent(String(v)),
}));
import { apiGet, apiPost } from "@/lib/api/client";
import {
  TRIVIA_API,
  triviaKeys,
  useLeaderboard,
  useMyStats,
  useSubmitAnswer,
  useTodayQuestion,
} from "@/plugins/example-trivia/hooks/useTrivia";

let client: QueryClient;
const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={client}>{children}</QueryClientProvider>
);

beforeEach(() => {
  vi.clearAllMocks();
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
});

describe("useTrivia hooks", () => {
  it("fetches today's question", async () => {
    vi.mocked(apiGet).mockResolvedValue({ question_id: "q1" });
    const { result } = renderHook(() => useTodayQuestion(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiGet).toHaveBeenCalledWith(`${TRIVIA_API}/questions/today`);
  });

  it("fetches leaderboard page", async () => {
    vi.mocked(apiGet).mockResolvedValue({
      entries: [],
      total_count: 0,
      pages: 1,
    });
    const { result } = renderHook(() => useLeaderboard(3), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiGet).toHaveBeenCalledWith(`${TRIVIA_API}/leaderboard?page=3`);
  });

  it("fetches my stats", async () => {
    vi.mocked(apiGet).mockResolvedValue({ rank: 1 });
    const { result } = renderHook(() => useMyStats(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiGet).toHaveBeenCalledWith(`${TRIVIA_API}/my-stats`);
  });

  it("submits answer and invalidates trivia queries", async () => {
    vi.mocked(apiPost).mockResolvedValue({ correct: true, streak: 2 });
    const inv = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useSubmitAnswer(), { wrapper });
    await act(() =>
      result.current.mutateAsync({ question_id: "q1", answer_id: "b" }),
    );
    expect(apiPost).toHaveBeenCalledWith(`${TRIVIA_API}/answers`, {
      question_id: "q1",
      answer_id: "b",
    });
    expect(inv).toHaveBeenCalledWith({ queryKey: triviaKeys.all });
  });
});
