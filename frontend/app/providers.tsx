"use client";
/**
 * @file app/providers.tsx
 * @brief Client-side provider tree. Wraps children with next-themes (class-based,
 *        system default), next-intl, and TanStack Query. Server state lives here; UI state lives in Zustand.
 */
import { useState } from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import {
  IsRestoringProvider,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { PERSIST_MAX_AGE } from "@/lib/pwa/queryPersist";
import { usePersistedCache } from "@/lib/pwa/usePersistedCache";
import { NextIntlClientProvider } from "next-intl";
import { useSession } from "@/stores/session";
import messages from "@/i18n/en-US.json";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Show cached data while offline instead of pausing the fetch.
            networkMode: "offlineFirst",
            gcTime: PERSIST_MAX_AGE,
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: (failures, err: unknown) => {
              const status = (err as { status?: number })?.status;
              if (status && status >= 400 && status < 500) return false;
              return failures < 2;
            },
          },
          // Offline mutations fail fast (UI also blocks via useOnline).
          mutations: { networkMode: "always" },
        },
      }),
  );

  const userId = useSession((s) => s.user?.id);
  // Restores + persists per signed-in user; also empties memory on purge.
  const isRestoring = usePersistedCache(queryClient, userId);

  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <NextIntlClientProvider locale="en-US" messages={messages} timeZone="UTC">
        <QueryClientProvider client={queryClient}>
          <IsRestoringProvider value={isRestoring}>
            {children}
          </IsRestoringProvider>
        </QueryClientProvider>
      </NextIntlClientProvider>
    </NextThemesProvider>
  );
}
