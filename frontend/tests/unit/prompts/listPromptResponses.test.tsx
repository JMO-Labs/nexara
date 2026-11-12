/**
 * @file tests/unit/prompts/listPromptResponses.test.tsx
 * @brief Tests listPromptResponses URL building and cursor pagination
 *        through useInfinitePromptResponses (nexara#256).
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { act, waitFor } from "@testing-library/react";

import * as client from "@/lib/api/client";
import { useInfinitePromptResponses } from "@/hooks/usePromptResponses";
import { renderHookWithProviders } from "../../utils/renderWithProviders";

vi.mock("@/lib/api/client", async (orig) => {
  const actual = await orig<typeof import("@/lib/api/client")>();
  return { ...actual, apiGet: vi.fn() };
});

const BASE = "/api/v1/prompts/posts/pp1/responses";

describe("useInfinitePromptResponses", () => {
  beforeEach(() => vi.clearAllMocks());

  it("requests first page without cursor, then next with cursor", async () => {
    vi.mocked(client.apiGet)
      .mockResolvedValueOnce({
        response_count: 2,
        items: [],
        next_cursor: "c1",
      })
      .mockResolvedValueOnce({
        response_count: 2,
        items: [],
        next_cursor: null,
      });
    const { result } = renderHookWithProviders(() =>
      useInfinitePromptResponses("pp1"),
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(client.apiGet).toHaveBeenNthCalledWith(1, `${BASE}?limit=20`);
    expect(result.current.hasNextPage).toBe(true);

    await act(async () => {
      await result.current.fetchNextPage();
    });
    expect(client.apiGet).toHaveBeenNthCalledWith(
      2,
      `${BASE}?limit=20&cursor=c1`,
    );
    await waitFor(() => expect(result.current.hasNextPage).toBe(false));
  });

  it("has no next page when next_cursor is null", async () => {
    vi.mocked(client.apiGet).mockResolvedValueOnce({
      response_count: 0,
      items: [],
      next_cursor: null,
    });
    const { result } = renderHookWithProviders(() =>
      useInfinitePromptResponses("pp1"),
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.hasNextPage).toBe(false);
    expect(client.apiGet).toHaveBeenCalledTimes(1);
  });
});
