"use client";
/**
 * @file hooks/useOnboarding.ts
 * @brief Onboarding wizard state query (shared by the gate, wizard and tour).
 */
import { useQuery } from "@tanstack/react-query";
import { getOnboarding } from "@/lib/api/onboarding";
import { useSession } from "@/stores/session";

export const ONBOARDING_KEY = ["onboarding"] as const;

/** @return query of the wizard state; enabled once signed in */
export function useOnboarding() {
  const authed = useSession((s) => s.status === "authenticated");
  return useQuery({
    queryKey: ONBOARDING_KEY,
    queryFn: getOnboarding,
    staleTime: 60_000,
    enabled: authed,
  });
}
