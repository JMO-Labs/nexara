"use client";
/**
 * @file hooks/useHomeChats.ts
 * @brief Home chats query, refreshed when realtime chat unread changes.
 */
import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import { getHomeChats } from "@/lib/api/home";
import { useChatRealtime } from "./useChat";

/**
 * @brief Fetch ranked home chat threads (stale after 30s).
 * @param limit Max threads (1..20).
 */
export function useHomeChats(limit = 4) {
  const qc = useQueryClient();
  const { unread } = useChatRealtime();
  const first = React.useRef(true);
  React.useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    void qc.invalidateQueries({ queryKey: qk.home.chats() });
  }, [unread, qc]);
  return useQuery({
    queryKey: [...qk.home.chats(), limit],
    queryFn: () => getHomeChats(limit),
    staleTime: 30_000,
  });
}
