/**
 * @file tests/unit/feed/useActivePrompts.test.tsx
 * @brief useActivePrompts hook and prompts API paths.
 */
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { vi, describe, it, expect } from "vitest";

const get = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/client", () => ({
  apiGet: get,
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
  seg: (s: string) => encodeURIComponent(s),
}));

import { useActivePrompts } from "@/hooks/useActivePrompts";
import { getPromptPost } from "@/lib/api/prompts";

describe("active prompts", () => {
  it("calls GET /api/v1/prompts/active", async () => {
    get.mockResolvedValue([{ id: "x" }]);
    const qc = new QueryClient();
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useActivePrompts(), { wrapper });
    await waitFor(() => expect(result.current.data).toEqual([{ id: "x" }]));
    expect(get).toHaveBeenCalledWith("/api/v1/prompts/active");
  });

  it("getPromptPost calls /api/v1/prompts/posts/{id}", async () => {
    get.mockResolvedValue({});
    await getPromptPost("abc");
    expect(get).toHaveBeenCalledWith("/api/v1/prompts/posts/abc");
  });
});
