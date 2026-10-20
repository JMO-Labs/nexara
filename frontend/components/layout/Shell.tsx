"use client";
/**
 * @file components/layout/Shell.tsx
 * @brief Authenticated app shell. Composes TopBar + Sidebar + main pane +
 *        MobileNav. Bootstraps the session and gates rendering on it.
 *        Global ? listener opens keyboard shortcuts modal.
 */
import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Box from "@mui/joy/Box";
import CircularProgress from "@mui/joy/CircularProgress";
import { useSession } from "@/stores/session";
import { useSessionBootstrap } from "@/hooks/useSession";
import { useModals } from "@/stores/modals";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";
import { MobileNav } from "./MobileNav";
import { ModalRoot } from "./ModalRoot";
import { KeyboardShortcutsModal } from "@/components/help/KeyboardShortcutsModal";
import { HelpButton } from "@/components/help/HelpButton";
import { OnboardingTour } from "@/components/onboarding/OnboardingTour";
import { WelcomeModal } from "@/components/onboarding/WelcomeModal";
import { FloatingChatDock } from "@/components/chat/FloatingChatDock";
import { RightRail } from "@/components/home/RightRail";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

export function Shell({ children }: { children: ReactNode }) {
  useSessionBootstrap();
  const router = useRouter();
  const status = useSession((s) => s.status);
  const setKeyboardShortcutsOpen = useModals((s) => s.setKeyboardShortcutsOpen);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  // Listen for hard auth failures (refresh exhausted) and force-redirect.
  // Only act when no user is currently set; a stale 401 from a request
  // started before re-login must not kick the freshly-logged-in user.
  useEffect(() => {
    function onAuthExpired() {
      if (useSession.getState().user) return;
      useSession.getState().setUser(null);
      router.replace("/login");
    }
    window.addEventListener("nx:auth-expired", onAuthExpired);
    return () => window.removeEventListener("nx:auth-expired", onAuthExpired);
  }, [router]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      // Ignore if user is typing in an input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;

      if (e.key === "?") {
        e.preventDefault();
        setKeyboardShortcutsOpen(true);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setKeyboardShortcutsOpen]);

  if (status === "unauthenticated") return null;

  const isBooting = status === "idle" || status === "loading";

  return (
    <Box
      sx={{
        minHeight: "100dvh",
        display: "flex",
        flexDirection: { xs: "column", md: "row" },
      }}
    >
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <Sidebar />
      <Box
        sx={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          height: "100dvh",
        }}
      >
        <TopBar />
        <Box
          id="main"
          component="main"
          sx={{
            position: "relative",
            flex: 1,
            minHeight: 0,
            overflow: "auto",
            p: { xs: 2, md: 3 },
            width: "100%",
            display: "flex",
            flexDirection: "column",
          }}
          aria-busy={isBooting || undefined}
        >
          {children}
          {isBooting && (
            <Box
              sx={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "var(--joy-palette-background-body)",
                zIndex: 10,
              }}
            >
              <CircularProgress />
            </Box>
          )}
        </Box>
        <MobileNav />
      </Box>
      {!isBooting && (
        <>
          <ModalRoot />
          <KeyboardShortcutsModal />
          <HelpButton />
          <WelcomeModal />
          <OnboardingTour />
          <FloatingChatDock />
          <RightRail />
          <ConfirmDialog />
        </>
      )}
    </Box>
  );
}
