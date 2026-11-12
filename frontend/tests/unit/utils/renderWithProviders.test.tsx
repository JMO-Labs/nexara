/**
 * @file renderWithProviders.test.tsx
 * @brief Verifies the shared provider wrapper for components and hooks.
 */
import { QueryClient, useQuery, useQueryClient } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import { useTheme } from "next-themes";
import {
  renderHookWithProviders,
  renderWithProviders,
} from "../../utils/renderWithProviders";

function ThemeProbe() {
  const { theme } = useTheme();
  return <span data-testid="theme">{theme ?? "none"}</span>;
}

describe("renderWithProviders", () => {
  it("provides next-themes context", () => {
    renderWithProviders(<ThemeProbe />);
    expect(screen.getByTestId("theme")).toBeInTheDocument();
  });

  it("uses a fresh client with retry disabled per call", () => {
    const a = renderHookWithProviders(() => useQueryClient());
    const b = renderHookWithProviders(() => useQueryClient());
    expect(a.result.current).not.toBe(b.result.current);
    expect(a.result.current.getDefaultOptions().queries?.retry).toBe(false);
  });

  it("accepts a caller-supplied client", () => {
    const queryClient = new QueryClient();
    const { result } = renderHookWithProviders(() => useQueryClient(), {
      queryClient,
    });
    expect(result.current).toBe(queryClient);
  });
});

describe("renderHookWithProviders", () => {
  it("resolves a useQuery hook", async () => {
    const { result } = renderHookWithProviders(() =>
      useQuery({ queryKey: ["x"], queryFn: async () => "ok" }),
    );
    await waitFor(() => expect(result.current.data).toBe("ok"));
  });

  it("does not retry failing queries", async () => {
    const fn = vi.fn().mockRejectedValue(new Error("boom"));
    const { result } = renderHookWithProviders(() =>
      useQuery({ queryKey: ["bad"], queryFn: fn }),
    );
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("exposes useTheme inside the wrapper", () => {
    const { result } = renderHookWithProviders(() => useTheme());
    expect(typeof result.current.setTheme).toBe("function");
  });
});
