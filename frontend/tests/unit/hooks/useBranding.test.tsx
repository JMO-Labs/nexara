/**
 * @file tests/unit/hooks/useBranding.test.tsx
 * @brief Unit tests for useBranding and useUpdateBranding.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { act, waitFor } from "@testing-library/react";

import * as brandingApi from "@/lib/api/branding";
import { useBranding, useUpdateBranding } from "@/hooks/useBranding";
import { useToasts } from "@/stores/toasts";
import { qk } from "@/lib/query-keys";
import { renderHookWithProviders } from "../../utils/renderWithProviders";

vi.mock("@/lib/api/branding");
vi.mock("next-intl", () => ({ useTranslations: () => (k: string) => k }));

describe("useBranding", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns branding on success", async () => {
    const data = { accent: "#123456" } as never;
    vi.mocked(brandingApi.getBranding).mockResolvedValue(data);
    const { result } = renderHookWithProviders(() => useBranding());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBe(data);
  });

  it("exposes error state on failure", async () => {
    vi.mocked(brandingApi.getBranding).mockRejectedValue(new Error("boom"));
    const { result } = renderHookWithProviders(() => useBranding());
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("boom");
  });
});

describe("useUpdateBranding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useToasts.getState().clear();
  });

  it("calls API, invalidates cache and toasts on success", async () => {
    vi.mocked(brandingApi.updateBranding).mockResolvedValue({} as never);
    const { result, queryClient } = renderHookWithProviders(() =>
      useUpdateBranding(),
    );
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    await act(async () => {
      await result.current.mutateAsync({ accent: "#000000" } as never);
    });
    expect(vi.mocked(brandingApi.updateBranding).mock.calls[0][0]).toEqual({
      accent: "#000000",
    });
    expect(spy).toHaveBeenCalledWith({ queryKey: qk.admin.branding() });
    expect(useToasts.getState().items).toEqual([
      expect.objectContaining({
        variant: "success",
        message: "Branding saved",
      }),
    ]);
  });

  it("does not invalidate on failure", async () => {
    vi.mocked(brandingApi.updateBranding).mockRejectedValue(new Error("x"));
    const { result, queryClient } = renderHookWithProviders(() =>
      useUpdateBranding(),
    );
    const spy = vi.spyOn(queryClient, "invalidateQueries");
    await act(async () => {
      await result.current.mutateAsync({} as never).catch(() => undefined);
    });
    expect(spy).not.toHaveBeenCalled();
  });
});
