/**
 * @file tests/unit/hooks/usePosts.test.ts
 * @brief Asserts usePosts mutations pass toast keys to useMutationWithToast.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { QueryClient } from "@tanstack/react-query";
import { qk } from "@/lib/query-keys";
import en from "@/i18n/en-US.json";

const qcHolder: { qc: unknown } = { qc: {} };
const spy = vi.fn((opts: unknown) => opts);
vi.mock("@/hooks/useMutationWithToast", () => ({
  useMutationWithToast: (opts: unknown) => spy(opts),
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => qcHolder.qc,
}));

import {
  useCreatePost,
  useDeletePost,
  useTogglePostReaction,
  useCreateComment,
} from "@/hooks/usePosts";

const last = () => spy.mock.results.at(-1)!.value as Record<string, unknown>;

describe("usePosts toast wiring", () => {
  beforeEach(() => spy.mockClear());

  it("createPost uses created key", () => {
    renderHook(() => useCreatePost());
    expect(last().successKey).toBe("toasts.posts.created");
  });
  it("deletePost uses deleted key", () => {
    renderHook(() => useDeletePost());
    expect(last().successKey).toBe("toasts.posts.deleted");
  });
  it("react is silent on success", () => {
    renderHook(() => useTogglePostReaction("p1"));
    expect(last().successKey).toBe("toasts.posts.reaction.added");
    expect(last().silentSuccess).toBe(true);
  });
  it("comment uses added key", () => {
    renderHook(() => useCreateComment("p1"));
    expect(last().successKey).toBe("toasts.comments.added");
  });
  it("all i18n keys exist in en-US", () => {
    const t = en.toasts;
    expect(t.posts.created).toBeTruthy();
    expect(t.posts.deleted).toBeTruthy();
    expect(t.posts.reaction.added).toBeTruthy();
    expect(t.comments.added).toBeTruthy();
    expect(t.errors.generic).toBeTruthy();
  });
});

type Opts = {
  onMutate: (e: string) => Promise<unknown>;
  onError: (err: Error, e: string, ctx: unknown) => void;
  onSettled: () => void;
};
const mkPost = () => ({
  id: "p1",
  reactions: [{ emoji: "x", count: 2, reacted_by_me: false }],
});

describe("useTogglePostReaction optimistic", () => {
  let qc: QueryClient;
  beforeEach(() => {
    spy.mockClear();
    qc = new QueryClient();
    qcHolder.qc = qc;
    qc.setQueryData(qk.feed.post("p1"), mkPost());
    qc.setQueryData(qk.feed.infinite({}), {
      pages: [{ items: [mkPost()] }],
      pageParams: [null],
    });
  });
  const opts = () => {
    renderHook(() => useTogglePostReaction("p1"));
    return last() as unknown as Opts;
  };
  const count = () =>
    (qc.getQueryData(qk.feed.post("p1")) as ReturnType<typeof mkPost>)
      .reactions[0].count;

  it("updates cache immediately", async () => {
    await opts().onMutate("x");
    expect(count()).toBe(3);
  });
  it("rolls back post and feed on error", async () => {
    const o = opts();
    const ctx = await o.onMutate("x");
    o.onError(new Error("boom"), "x", ctx);
    expect(count()).toBe(2);
    const feed = qc.getQueryData(qk.feed.infinite({})) as {
      pages: { items: ReturnType<typeof mkPost>[] }[];
    };
    expect(feed.pages[0].items[0].reactions[0].count).toBe(2);
  });
  it("invalidates on settled", () => {
    const inv = vi.spyOn(qc, "invalidateQueries");
    opts().onSettled();
    expect(inv).toHaveBeenCalledWith({ queryKey: qk.feed.all() });
  });
});
