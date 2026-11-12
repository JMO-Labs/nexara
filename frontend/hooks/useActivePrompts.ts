/**
 * @file hooks/useActivePrompts.ts
 * @brief Query hook for active prompts shown at the top of the home feed.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getActivePrompts } from "@/lib/api/prompts";

/**
 * @brief Fetch active prompt posts.
 * @return Query result with PromptPost[]
 */
export function useActivePrompts() {
  return useQuery({
    queryKey: qk.feed.activePrompts(),
    queryFn: getActivePrompts,
    staleTime: 60_000,
  });
}
