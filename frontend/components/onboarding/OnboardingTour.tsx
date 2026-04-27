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

const Joyride = dynamic(
  () => import('react-joyride').then((mod) => mod.Joyride),
  { ssr: false }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
) as any;

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
