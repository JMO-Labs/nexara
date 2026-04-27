'use client';
/**
 * @file components/layout/Shell.tsx
 * @brief Authenticated app shell. Composes TopBar + Sidebar + main pane +
 *        MobileNav. Bootstraps the session and gates rendering on it.
 *        Global ? listener opens keyboard shortcuts modal.
 */
import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Box from '@mui/joy/Box';
import CircularProgress from '@mui/joy/CircularProgress';
import { useSession } from '@/stores/session';
import { useSessionBootstrap } from '@/hooks/useSession';
import { useModals } from '@/stores/modals';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { ModalRoot } from './ModalRoot';
import { KeyboardShortcutsModal } from '@/components/help/KeyboardShortcutsModal';
import { OnboardingTour } from '@/components/onboarding/OnboardingTour';

export function Shell({ children }: { children: ReactNode }) {
  useSessionBootstrap();
  const router = useRouter();
  const status = useSession((s) => s.status);
  const setKeyboardShortcutsOpen = useModals((s) => s.setKeyboardShortcutsOpen);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.replace('/login');
    }
  }, [status, router]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      // Ignore if user is typing in an input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

      if (e.key === '?') {
        e.preventDefault();
        setKeyboardShortcutsOpen(true);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [setKeyboardShortcutsOpen]);

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
      <KeyboardShortcutsModal />
      <OnboardingTour />
    </Box>
  );
}
