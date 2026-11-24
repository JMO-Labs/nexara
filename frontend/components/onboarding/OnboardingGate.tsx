"use client";
/**
 * @file components/onboarding/OnboardingGate.tsx
 * @brief Sends members who have not finished onboarding to /app/welcome.
 *        Auth routes and the SSO test page live outside /app, so only
 *        /app/** needs the exemption for the wizard itself.
 */
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useOnboarding } from "@/hooks/useOnboarding";

export const WELCOME_PATH = "/app/welcome";

/**
 * @return ``pending`` (false while loading), ``loaded``, and ``hold``: show a
 *         loader instead of page content while the state loads or a redirect
 *         to the wizard is due (no content flash). Errors release the hold.
 */
export function useOnboardingGate(): {
  pending: boolean;
  loaded: boolean;
  hold: boolean;
} {
  const router = useRouter();
  const pathname = usePathname();
  const { data, isLoading } = useOnboarding();
  const pending = !!data && !data.done;
  const exempt =
    !pathname.startsWith("/app") ||
    pathname.startsWith(WELCOME_PATH) ||
    pathname.startsWith("/sso-test");
  useEffect(() => {
    if (pending && !exempt) router.replace(WELCOME_PATH);
  }, [pending, exempt, router]);
  return {
    pending,
    loaded: !!data,
    hold: !exempt && (isLoading || pending),
  };
}
