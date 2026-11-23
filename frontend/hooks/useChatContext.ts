"use client";
/**
 * @file hooks/useChatContext.ts
 * @brief Query hook for the conversation details payload.
 */
import { useQuery } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getChatContext } from "@/lib/api/chatContext";

/**
 * @brief Fetch details for a channel (stale after 60s).
 * @param channelId channel id or null (disabled)
 */
export function useChatContext(channelId: string | null) {
  return useQuery({
    queryKey: qk.chat.context(channelId ?? ""),
    queryFn: () => getChatContext(channelId!),
    enabled: Boolean(channelId),
    staleTime: 60_000,
  });
}
