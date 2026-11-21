"use client";
/**
 * @file hooks/useSignOut.ts
 * @brief Shared sign-out action: API logout, clear token + session, redirect.
 */
import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/stores/session";
import { logout as apiLogout } from "@/lib/api/auth";
import { setAccessToken } from "@/lib/auth/session";

/**
 * @brief Build the sign-out handler.
 * @return async function that signs the user out and routes to /login
 */
export function useSignOut(): () => Promise<void> {
  const router = useRouter();
  const reset = useSession((s) => s.reset);
  return useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      /* local state is what matters */
    }
    setAccessToken(null);
    reset();
    router.replace("/login");
  }, [router, reset]);
}
