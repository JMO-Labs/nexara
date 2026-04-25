'use client';
/**
 * @file components/layout/Shell.tsx
 * @brief Authenticated app shell. Composes TopBar + Sidebar + main pane +
 *        MobileNav. Bootstraps the session and gates rendering on it.
 */
import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Box from '@mui/joy/Box';
import CircularProgress from '@mui/joy/CircularProgress';
import { useSession } from '@/stores/session';
import { useSessionBootstrap } from '@/hooks/useSession';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { ModalRoot } from './ModalRoot';

export function Shell({ children }: { children: ReactNode }) {
  useSessionBootstrap();
  const router = useRouter();
  const status = useSession((s) => s.status);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.replace('/login');
    }
  }, [status, router]);

  if (status === 'unauthenticated') return null;

  if (status === 'idle' || status === 'loading') {
    return (
      <Box
        sx={{
          minHeight: '100dvh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        aria-busy
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: '100dvh',
        display: 'flex',
        flexDirection: { xs: 'column', md: 'row' },
      }}
    >
      <a href="#main" className="skip-link">Skip to main content</a>
      <Sidebar />
      <Box
        sx={{
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100dvh',
        }}
      >
        <TopBar />
        <Box
          id="main"
          component="main"
          sx={{
            flex: 1,
            p: { xs: 2, md: 3 },
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {children}
        </Box>
        <MobileNav />
      </Box>
      <ModalRoot />
    </Box>
  );
}
