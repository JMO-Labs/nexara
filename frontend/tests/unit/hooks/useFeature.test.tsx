/**
 * @file tests/unit/hooks/useFeature.test.tsx
 * @brief useFeature: loading defaults, then server values.
 */
import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import * as api from "@/lib/api/features";
import { useFeature } from "@/hooks/useFeature";

vi.mock("@/lib/api/features", async (orig) => ({
  ...(await orig<typeof api>()),
  getFeatures: vi.fn(),
}));

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe("useFeature", () => {
  it("defaults while loading", () => {
    vi.mocked(api.getFeatures).mockReturnValue(new Promise(() => {}));
    const w = wrap();
    expect(
      renderHook(() => useFeature("recipes"), { wrapper: w }).result.current,
    ).toBe(true);
    expect(
      renderHook(() => useFeature("reply_by_email"), { wrapper: w }).result
        .current,
    ).toBe(false);
  });

  it("uses the server value once loaded", async () => {
    vi.mocked(api.getFeatures).mockResolvedValue({
      recipes: false,
      reply_by_email: true,
    } as api.Features);
    const { result } = renderHook(() => useFeature("recipes"), {
      wrapper: wrap(),
    });
    await waitFor(() => expect(result.current).toBe(false));
  });
});
