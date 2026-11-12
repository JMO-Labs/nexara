/**
 * @file plugins/example-trivia/hooks/useTrivia.ts
 * @brief TanStack Query hooks for the example-trivia plugin API.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api/client";

export const TRIVIA_API = "/api/v1/plugins/example-trivia";

export interface TriviaOption {
  id: string;
  text: string;
}

export interface TodayQuestion {
  question_id: string;
  text: string;
  options: TriviaOption[];
  answered_today: boolean;
  user_answer_id?: string;
  /** Current streak; optional, present once the user has answered before. */
  streak?: number;
}

export interface AnswerInput {
  question_id: string;
  answer_id: string;
}

export interface AnswerResult {
  correct: boolean;
  streak: number;
}

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  user_name: string;
  streak: number;
  total_correct: number;
}

export interface Leaderboard {
  entries: LeaderboardEntry[];
  total_count: number;
  pages: number;
}

export interface MyStats {
  rank: number;
  streak: number;
  best_streak: number;
  total_correct: number;
  total_answers: number;
  percentage_correct: number;
  days_participated: number;
  first_answer_at: string | null;
  last_answer_at: string | null;
}

export const triviaKeys = {
  all: ["plugin", "example-trivia"] as const,
  today: () => [...triviaKeys.all, "today"] as const,
  leaderboard: (page: number) =>
    [...triviaKeys.all, "leaderboard", page] as const,
  myStats: () => [...triviaKeys.all, "my-stats"] as const,
};

const MIN = 60_000;

/** @brief Today's question. @return query result */
export function useTodayQuestion() {
  return useQuery({
    queryKey: triviaKeys.today(),
    queryFn: () => apiGet<TodayQuestion>(`${TRIVIA_API}/questions/today`),
    staleTime: 5 * MIN,
    gcTime: 30 * MIN,
  });
}

/** @brief Submit an answer; invalidates all trivia queries on success. */
export function useSubmitAnswer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AnswerInput) =>
      apiPost<AnswerResult>(`${TRIVIA_API}/answers`, input),
    onSuccess: () => qc.invalidateQueries({ queryKey: triviaKeys.all }),
  });
}

/** @brief Leaderboard page (25 per page). @param page 1-based page */
export function useLeaderboard(page: number = 1) {
  return useQuery({
    queryKey: triviaKeys.leaderboard(page),
    queryFn: () =>
      apiGet<Leaderboard>(`${TRIVIA_API}/leaderboard?page=${page}`),
    staleTime: MIN,
    gcTime: 10 * MIN,
    placeholderData: (prev) => prev,
  });
}

/** @brief Current user's detailed stats. */
export function useMyStats() {
  return useQuery({
    queryKey: triviaKeys.myStats(),
    queryFn: () => apiGet<MyStats>(`${TRIVIA_API}/my-stats`),
    staleTime: MIN,
    gcTime: 10 * MIN,
  });
}
