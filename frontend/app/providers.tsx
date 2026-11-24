"use client";
/**
 * @file app/providers.tsx
 * @brief Client-side provider tree. Wraps children with next-themes (class-based,
 *        system default), next-intl, and TanStack Query. Server state lives here; UI state lives in Zustand.
 */
import { useEffect, useRef, useState } from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import { QueryClient } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import {
  PERSIST_BUSTER,
  PERSIST_MAX_AGE,
  createPersister,
  shouldPersist,
} from "@/lib/pwa/queryPersist";
import { CLEAR_EVENT } from "@/lib/pwa/clearUserCache";
import { NextIntlClientProvider } from "next-intl";
import { loadPlugins } from "@/lib/plugins/plugin-loader";
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
        },
      }),
  );

  const [persister] = useState(createPersister);
  useEffect(() => {
    const clear = () => queryClient.clear();
    window.addEventListener(CLEAR_EVENT, clear);
    return () => window.removeEventListener(CLEAR_EVENT, clear);
  }, [queryClient]);

  // The plugin manifest needs auth: load once, after the session is restored.
  const authed = useSession((s) => s.status === "authenticated");
  const pluginsLoaded = useRef(false);
  useEffect(() => {
    if (!authed || pluginsLoaded.current) return;
    pluginsLoaded.current = true;
    void loadPlugins();
  }, [authed]);

  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <NextIntlClientProvider locale="en-US" messages={messages} timeZone="UTC">
        <PersistQueryClientProvider
          client={queryClient}
          persistOptions={{
            persister: persister ??
              // No IndexedDB (SSR/old browsers): in-memory no-op persister.
              {
                persistClient: async () => {},
                restoreClient: async () => undefined,
                removeClient: async () => {},
              },
            maxAge: PERSIST_MAX_AGE,
            buster: PERSIST_BUSTER,
            dehydrateOptions: { shouldDehydrateQuery: shouldPersist },
          }}
        >
          {children}
        </PersistQueryClientProvider>
      </NextIntlClientProvider>
    </NextThemesProvider>
  );
}
