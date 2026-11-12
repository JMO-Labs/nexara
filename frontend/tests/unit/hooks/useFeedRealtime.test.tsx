/**
 * @file tests/unit/hooks/useFeedRealtime.test.tsx
 * @brief useFeedRealtime applies SSE feed_update events to the query cache.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useFeedRealtime } from "@/hooks/useFeedRealtime";
import { qk } from "@/lib/query-keys";
import { renderHookWithProviders } from "../../utils/renderWithProviders";

type Handler = (data: unknown, type: string) => void;
let handler: Handler;
const useSSEMock = vi.fn();
vi.mock("@/hooks/useSSE", () => ({
  useSSE: (path: string, opts: { onMessage: Handler }) => {
    useSSEMock(path, opts);
    handler = opts.onMessage;
  },
}));

const post = (id: string, extra: object = {}) =>
  ({ id, comment_count: 0, reactions: [], ...extra }) as never;
const infinite = (items: unknown[]) => ({
  pages: [{ items, next_cursor: null }],
  pageParams: [undefined],
});

describe("useFeedRealtime", () => {
  beforeEach(() => vi.clearAllMocks());

  it("subscribes to feed_update events", () => {
    renderHookWithProviders(() => useFeedRealtime());
    expect(useSSEMock.mock.calls[0][1].eventTypes).toEqual(["feed_update"]);
  });

  it("prepends a created post to the feed cache once", () => {
    const { queryClient } = renderHookWithProviders(() => useFeedRealtime());
    const key = qk.feed.infinite();
    queryClient.setQueryData(key, infinite([post("a")]));
    const msg = { event: "created", post: post("b") };
    handler(msg, "feed_update");
    handler(msg, "feed_update");
    const data = queryClient.getQueryData<{
      pages: { items: { id: string }[] }[];
    }>(key);
    expect(data?.pages[0].items.map((i) => i.id)).toEqual(["b", "a"]);
  });

  it("bumps comment count and invalidates comments", () => {
    const { queryClient } = renderHookWithProviders(() => useFeedRealtime());
    queryClient.setQueryData(qk.feed.post("a"), post("a"));
    queryClient.setQueryData(qk.feed.infinite(), infinite([post("a")]));
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    handler(
      { event: "comment_created", post_id: "a", comment: { id: "c" } },
      "feed_update",
    );
    expect(
      queryClient.getQueryData<{ comment_count: number }>(qk.feed.post("a"))
        ?.comment_count,
    ).toBe(1);
    const list = queryClient.getQueryData<{
      pages: { items: { comment_count: number }[] }[];
    }>(qk.feed.infinite());
    expect(list?.pages[0].items[0].comment_count).toBe(1);
    expect(spy).toHaveBeenCalledWith({ queryKey: qk.feed.comments("a") });
  });

  it("syncs reaction counts", () => {
    const { queryClient } = renderHookWithProviders(() => useFeedRealtime());
    queryClient.setQueryData(qk.feed.post("a"), post("a"));
    handler(
      {
        event: "reaction_toggled",
        target_type: "post",
        post_id: "a",
        emoji: "x",
        count: 2,
      },
      "feed_update",
    );
    expect(
      queryClient.getQueryData<{ reactions: unknown[] }>(qk.feed.post("a"))
        ?.reactions,
    ).toEqual([{ emoji: "x", count: 2, reacted_by_me: false }]);
    handler(
      {
        event: "reaction_toggled",
        target_type: "post",
        post_id: "a",
        emoji: "x",
        count: 0,
      },
      "feed_update",
    );
    expect(
      queryClient.getQueryData<{ reactions: unknown[] }>(qk.feed.post("a"))
        ?.reactions,
    ).toEqual([]);
  });

  it("ignores other event types and bad payloads", () => {
    const { queryClient } = renderHookWithProviders(() => useFeedRealtime());
    queryClient.setQueryData(qk.feed.post("a"), post("a"));
    handler({ event: "comment_created", post_id: "a", comment: {} }, "other");
    handler(null, "feed_update");
    handler("str", "feed_update");
    expect(
      queryClient.getQueryData<{ comment_count: number }>(qk.feed.post("a"))
        ?.comment_count,
    ).toBe(0);
  });
});
