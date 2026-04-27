/**
 * @file OnboardingTour.tsx
 * @brief Joyride-based guided tour runner for onboarding.
 *
 * Manages tour lifecycle, persistence to backend, and SSR-safe dynamic import.
 */

'use client';

import dynamic from 'next/dynamic';
import { useSession } from '@/stores/session';
import { memberTour, adminTour } from '@/lib/onboarding/tours';
import * as usersApi from '@/lib/api/users';

// @ts-expect-error react-joyride types don't align with next/dynamic properly
const Joyride = dynamic(
  async () => {
    const mod = await import('react-joyride');
    return mod;
  },
  { ssr: false }
);

export function OnboardingTour() {
  const user = useSession((s) => s.user);

  if (!user) return null;

  // Determine tour visibility based on user state
  const shouldRun = !user.tour_completed_at;
  const steps = user.is_admin ? adminTour : memberTour;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleTourCallback = (data: any) => {
    // Mark onboarding as complete when user finishes or skips
    if (['finished', 'skipped'].includes(data.status)) {
      void usersApi.completeOnboarding();
    }
  };

  return (
    <Joyride
      steps={steps}
      run={shouldRun}
      continuous
      showSkipButton
      callback={handleTourCallback}
    />
  );
}
