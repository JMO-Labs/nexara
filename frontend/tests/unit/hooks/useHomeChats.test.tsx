/**
 * @file tests/unit/hooks/useHomeChats.test.tsx
 * @brief useHomeChats: fetches, and refetches when realtime unread changes.
 */
import { waitFor, act } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { renderHookWithProviders } from "../../utils/renderWithProviders";

let unread: Record<string, number> = {};
vi.mock("@/hooks/useChat", () => ({
  useChatRealtime: () => ({ unread }),
}));
vi.mock("@/lib/api/home", () => ({ getHomeChats: vi.fn() }));

import { useHomeChats } from "@/hooks/useHomeChats";
import * as api from "@/lib/api/home";

describe("useHomeChats", () => {
  it("fetches with limit and refetches on unread change", async () => {
    vi.mocked(api.getHomeChats).mockResolvedValue({ items: [] });
    const { result, rerender } = renderHookWithProviders(() => useHomeChats(4));
    await waitFor(() => expect(result.current.data).toEqual({ items: [] }));
    expect(api.getHomeChats).toHaveBeenCalledWith(4);
    expect(api.getHomeChats).toHaveBeenCalledTimes(1);
    unread = { c1: 1 };
    await act(async () => rerender());
    await waitFor(() => expect(api.getHomeChats).toHaveBeenCalledTimes(2));
  });
});
