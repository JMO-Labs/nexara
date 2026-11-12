"use client";
/**
 * @file plugins/example-trivia/hooks/useTriviaWebSocket.ts
 * @brief Refetches the leaderboard on "trivia:leaderboard_updated" realtime
 *        events (delivered over the shared notifications SSE stream).
 */
import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSSE } from "@/hooks/useSSE";
import { STREAM_PATH } from "@/lib/api/notifications";
import { triviaKeys } from "./useTrivia";

export const LEADERBOARD_EVENT = "trivia:leaderboard_updated";
const EVENT_TYPES = [LEADERBOARD_EVENT] as const;

/** @brief Subscribe while @p enabled (e.g. leaderboard open). */
export function useTriviaWebSocket(enabled: boolean = true): void {
  const qc = useQueryClient();
  const onMessage = useCallback(
    (_data: unknown, type: string) => {
      if (type === LEADERBOARD_EVENT)
        void qc.invalidateQueries({
          queryKey: [...triviaKeys.all, "leaderboard"],
        });
    },
    [qc],
  );
  useSSE(STREAM_PATH, { enabled, eventTypes: EVENT_TYPES, onMessage });
}
