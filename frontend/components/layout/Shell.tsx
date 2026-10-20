"use client";
/**
 * @file components/layout/Shell.tsx
 * @brief Authenticated app shell. Composes SideNav + TopBar + main pane +
 *        BottomTabBar. Bootstraps the session and gates rendering on it.
 *        Global ? listener opens keyboard shortcuts modal.
 */
import type { ReactNode } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSession } from "@/stores/session";
import { useSessionBootstrap } from "@/hooks/useSession";
import { useModals } from "@/stores/modals";
import { TopBar } from "./TopBar";
import { SideNav } from "./SideNav";
import { BottomTabBar, TAB_BAR_CLEARANCE } from "./BottomTabBar";
import { ModalRoot } from "./ModalRoot";
import { KeyboardShortcutsModal } from "@/components/help/KeyboardShortcutsModal";
import { HelpButton } from "@/components/help/HelpButton";
import { OnboardingTour } from "@/components/onboarding/OnboardingTour";
import { WelcomeModal } from "@/components/onboarding/WelcomeModal";
import { FloatingChatDock } from "@/components/chat/FloatingChatDock";
import { RightRail } from "@/components/home/RightRail";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { TooltipProvider } from "@/components/ui/Tooltip";

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
    <TooltipProvider>
      <div className="bg-bg text-ink min-h-dvh">
        <a
          href="#main"
          className="bg-surface-strong text-accent focus:outline-accent sr-only z-50 rounded-xl px-4 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:outline-2 focus:outline-offset-2"
        >
          Skip to content
        </a>
        <SideNav />
        <div className="flex min-h-dvh min-w-0 flex-col md:pl-16">
          <TopBar />
          <main
            id="main"
            className={cn("relative flex-1 px-4 md:px-8", TAB_BAR_CLEARANCE)}
            aria-busy={isBooting || undefined}
          >
            {children}
            {isBooting && (
              <div className="bg-bg absolute inset-0 z-10 flex items-center justify-center">
                <Loader2
                  aria-label="Loading"
                  className="size-6 motion-safe:animate-spin"
                />
              </div>
            )}
          </main>
          <BottomTabBar />
        </div>
        {!isBooting && (
          <>
            <ModalRoot />
            <KeyboardShortcutsModal />
            <HelpButton />
            <WelcomeModal />
            <OnboardingTour />
            <div className="hidden md:block">
              <FloatingChatDock />
            </div>
            <RightRail />
            <ConfirmDialog />
          </>
        )}
      </div>
    </TooltipProvider>
  );
}
