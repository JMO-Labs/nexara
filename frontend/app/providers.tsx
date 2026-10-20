"use client";
/**
 * @file app/providers.tsx
 * @brief Client-side provider tree. Wraps children with next-themes (class-based,
 *        system default), next-intl, and TanStack Query. Server state lives here; UI state lives in Zustand.
 */
import { useState } from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/i18n/en-US.json";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
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

  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <NextIntlClientProvider locale="en-US" messages={messages} timeZone="UTC">
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      </NextIntlClientProvider>
    </NextThemesProvider>
  );
}
