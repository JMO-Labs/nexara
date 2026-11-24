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

/** @return whether onboarding is pending (false while loading) and the redirect side effect */
export function useOnboardingGate(): { pending: boolean; loaded: boolean } {
  const router = useRouter();
  const pathname = usePathname();
  const { data } = useOnboarding();
  const pending = !!data && !data.done;
  const exempt =
    !pathname.startsWith("/app") ||
    pathname.startsWith(WELCOME_PATH) ||
    pathname.startsWith("/sso-test");
  useEffect(() => {
    if (pending && !exempt) router.replace(WELCOME_PATH);
  }, [pending, exempt, router]);
  return { pending, loaded: !!data };
}
