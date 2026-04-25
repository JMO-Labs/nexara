'use client';
/**
 * @file app/providers.tsx
 * @brief Client-side provider tree. Wraps children with Emotion cache,
 *        Joy CSS-vars provider, next-themes (system/dark/light), and
 *        TanStack Query. Server state lives here; UI state lives in Zustand.
 */
import { useState } from 'react';
import { CssVarsProvider } from '@mui/joy/styles';
import CssBaseline from '@mui/joy/CssBaseline';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import EmotionRegistry from '@/theme/EmotionRegistry';
import joyTheme from '@/theme/joy-theme';
import messages from '@/i18n/en-US.json';

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
    <EmotionRegistry>
      <NextThemesProvider
        attribute="data-joy-color-scheme"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <CssVarsProvider
          theme={joyTheme}
          defaultMode="system"
          modeStorageKey="nx-mode"
          colorSchemeStorageKey="nx-color-scheme"
        >
          <CssBaseline />
          <NextIntlClientProvider locale="en-US" messages={messages} timeZone="UTC">
            <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
          </NextIntlClientProvider>
        </CssVarsProvider>
      </NextThemesProvider>
    </EmotionRegistry>
  );
}
