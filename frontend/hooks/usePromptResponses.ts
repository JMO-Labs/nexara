/**
 * @file hooks/usePromptResponses.ts
 * @brief Live response count hook with 30s refetch interval.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getPromptResponseCount } from "@/lib/api/prompts";

/**
 * @brief Query hook to fetch response count for a prompt post (auto-refetch every 30s).
 * @param promptPostId Prompt post ID
 * @return Query result with response_count
 */
export function usePromptResponses(promptPostId?: string) {
  return useQuery({
    queryKey: qk.feed.promptResponses(promptPostId ?? ""),
    queryFn: () =>
      promptPostId
        ? getPromptResponseCount(promptPostId)
        : Promise.reject("No ID"),
    enabled: !!promptPostId,
    staleTime: 0,
    refetchInterval: 30_000, // Refetch every 30 seconds
  });
}
