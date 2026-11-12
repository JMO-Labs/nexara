/**
 * @file OnboardingTour.tsx
 * @brief Joyride-based guided tour runner for onboarding.
 *
 * Manages tour lifecycle, persistence to backend, and SSR-safe dynamic import.
 */

"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import { useSession } from "@/stores/session";
import { memberTour, adminTour } from "@/lib/onboarding/tours";
import * as usersApi from "@/lib/api/users";

const Joyride = dynamic(
  () => import("react-joyride").then((mod) => mod.Joyride),
  { ssr: false },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
) as any;

/** @brief Token-based tooltip theme (CSS vars follow light/dark). */
const TOUR_OPTIONS = {
  // hex: joyride derives the beacon rgba from it
  primaryColor: "#14301E",
  backgroundColor: "var(--nx-surface)",
  arrowColor: "var(--nx-surface)",
  textColor: "var(--nx-ink)",
  overlayColor: "rgba(0, 0, 0, 0.5)",
  zIndex: 1400,
};

/** @brief AA pairs: lilac on forest for Next, ink for Back (accent fails on white). */
const TOUR_STYLES = {
  buttonPrimary: {
    backgroundColor: "var(--nx-surface-strong)",
    color: "var(--nx-accent)",
  },
  buttonBack: { color: "var(--nx-ink)" },
};

const TERMINAL = new Set(["finished", "skipped", "error"]);

export function OnboardingTour() {
  const user = useSession((s) => s.user);
  const setUser = useSession((s) => s.setUser);
  const [run, setRun] = React.useState<boolean>(false);
  const [done, setDone] = React.useState<boolean>(false);

  React.useEffect(() => {
    if (user && !user.tour_completed_at && !done) {
      setRun(true);
    } else {
      setRun(false);
    }
  }, [user, done]);

  if (!user) return null;
  if (done || user.tour_completed_at) return null;

  const steps = user.is_admin ? adminTour : memberTour;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleTourCallback = (data: any) => {
    const status: string = data?.status ?? "";
    const action: string = data?.action ?? "";
    if (TERMINAL.has(status) || action === "close" || action === "reset") {
      setRun(false);
      setDone(true);
      setUser({ ...user, tour_completed_at: new Date().toISOString() });
      void usersApi.completeOnboarding().catch(() => undefined);
    }
  };

  return (
    <Joyride
      steps={steps}
      run={run}
      continuous
      showSkipButton
      disableScrolling
      options={TOUR_OPTIONS}
      styles={TOUR_STYLES}
      callback={handleTourCallback}
    />
  );
}
