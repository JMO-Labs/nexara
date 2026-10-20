"use client";
/**
 * @file hooks/useHomeFeed.ts
 * @brief Unified home feed: infinite query + SSE-driven head refetch.
 *        New items buffer in `pending` when the reader is scrolled down.
 */
import * as React from "react";
import {
  useInfiniteQuery,
  useQueryClient,
  type InfiniteData,
} from "@tanstack/react-query";
import { useSSE } from "./useSSE";
import { qk } from "@/lib/query-keys";
import { STREAM_PATH } from "@/lib/api/notifications";
import {
  getHomeFeed,
  type FeedItem,
  type HomeFeedResponse,
} from "@/lib/api/home";

const AT_TOP_PX = 120;
const FRESH_MS = 2000;
const key = (i: FeedItem) => `${i.kind}:${i.id}`;

/**
 * @brief Home feed state and realtime handling.
 * @return items, paging, pending buffer, reveal(), freshIds (just revealed)
 */
export function useHomeFeed() {
  const qc = useQueryClient();
  const q = useInfiniteQuery({
    queryKey: qk.home.feed(),
    queryFn: ({ pageParam }) => getHomeFeed(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    staleTime: 60_000,
  });

  const items = React.useMemo(() => {
    const seen = new Set<string>();
    return (q.data?.pages ?? [])
      .flatMap((p) => p.items)
      .filter((i) => !seen.has(key(i)) && !!seen.add(key(i)));
  }, [q.data]);

  const [pending, setPending] = React.useState<FeedItem[]>([]);
  const [freshIds, setFreshIds] = React.useState<Set<string>>(new Set());
  const itemsRef = React.useRef(items);
  const pendingRef = React.useRef(pending);
  React.useEffect(() => {
    itemsRef.current = items;
    pendingRef.current = pending;
  });
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const prepend = React.useCallback(
    (add: FeedItem[]) => {
      if (add.length === 0) return;
      qc.setQueryData<InfiniteData<HomeFeedResponse, string | undefined>>(
        qk.home.feed(),
        (old) => {
          if (!old || old.pages.length === 0) return old;
          const pages = [...old.pages];
          pages[0] = { ...pages[0], items: [...add, ...pages[0].items] };
          return { ...old, pages };
        },
      );
      setFreshIds(new Set(add.map((i) => key(i))));
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setFreshIds(new Set()), FRESH_MS);
    },
    [qc],
  );
  React.useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const onMessage = React.useCallback(
    async (_d: unknown, type: string) => {
      if (type !== "feed_ping" && type !== "feed_update") return;
      if (!q.data) return;
      let head: HomeFeedResponse;
      try {
        head = await getHomeFeed();
      } catch {
        return;
      }
      const known = new Set(itemsRef.current.map(key));
      pendingRef.current.forEach((i) => known.add(key(i)));
      const fresh = head.items.filter((i) => !known.has(key(i)));
      if (fresh.length === 0) return;
      if (window.scrollY < AT_TOP_PX) prepend(fresh);
      else setPending((p) => [...fresh, ...p]);
    },
    [q.data, prepend],
  );

  useSSE(STREAM_PATH, {
    onMessage,
    eventTypes: ["feed_ping", "feed_update"],
  });

  const reveal = React.useCallback(() => {
    prepend(pendingRef.current);
    setPending([]);
  }, [prepend]);

  return {
    items,
    fetchNextPage: q.fetchNextPage,
    hasNextPage: q.hasNextPage,
    isLoading: q.isLoading,
    pending,
    reveal,
    freshIds,
  };
}
