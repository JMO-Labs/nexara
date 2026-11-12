/**
 * @file renderWithProviders.tsx
 * @brief Test helpers wrapping UI/hooks in QueryClient + next-themes providers.
 */
import type { ReactElement, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import {
  render,
  renderHook,
  type RenderHookOptions,
  type RenderOptions,
} from "@testing-library/react";

/** @brief Extra options: optionally supply your own QueryClient. */
export interface ProviderOptions {
  queryClient?: QueryClient;
}

/** @brief Create a QueryClient with retries disabled. */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ThemeProvider attribute="class">{children}</ThemeProvider>
      </QueryClientProvider>
    );
  };
}

/**
 * @brief Render UI inside the app providers.
 * @param ui Element to render.
 * @param opts RTL options plus optional queryClient.
 * @return RTL result plus the queryClient used.
 */
export function renderWithProviders(
  ui: ReactElement,
  opts: Omit<RenderOptions, "wrapper"> & ProviderOptions = {},
) {
  const { queryClient = createTestQueryClient(), ...rest } = opts;
  return {
    queryClient,
    ...render(ui, { wrapper: makeWrapper(queryClient), ...rest }),
  };
}

/**
 * @brief Render a hook inside the app providers.
 * @param hook Hook callback.
 * @param opts RTL hook options plus optional queryClient.
 * @return RTL hook result plus the queryClient used.
 */
export function renderHookWithProviders<Result, Props>(
  hook: (props: Props) => Result,
  opts: Omit<RenderHookOptions<Props>, "wrapper"> & ProviderOptions = {},
) {
  const { queryClient = createTestQueryClient(), ...rest } = opts;
  return {
    queryClient,
    ...renderHook(hook, { wrapper: makeWrapper(queryClient), ...rest }),
  };
}
