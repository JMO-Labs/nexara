/**
 * @file tests/unit/hooks/usePosts.test.ts
 * @brief Asserts usePosts mutations pass toast keys to useMutationWithToast.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import en from "@/i18n/en-US.json";

const spy = vi.fn((opts: unknown) => opts);
vi.mock("@/hooks/useMutationWithToast", () => ({
  useMutationWithToast: (opts: unknown) => spy(opts),
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => ({}),
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
