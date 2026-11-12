/**
 * @file hooks/usePromptResponses.ts
 * @brief Live response count hook with 30s refetch interval.
 */
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getPromptResponseCount, listPromptResponses } from "@/lib/api/prompts";

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

/**
 * @brief Infinite query for response posts of a prompt post.
 * @param promptPostId Prompt post ID
 * @return Infinite query result; next page driven by next_cursor
 */
export function useInfinitePromptResponses(promptPostId?: string) {
  return useInfiniteQuery({
    queryKey: [...qk.feed.promptResponses(promptPostId ?? ""), "list"],
    queryFn: ({ pageParam }) =>
      listPromptResponses(promptPostId!, pageParam as string | null),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    enabled: !!promptPostId,
  });
}
