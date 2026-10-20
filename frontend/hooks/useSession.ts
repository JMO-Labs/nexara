"use client";
/**
 * @file hooks/useSession.ts
 * @brief Bootstraps the auth session on cold load: tries to refresh the
 *        access token from the HttpOnly cookie, then fetches /users/me.
 *        Skips entirely when the session store already holds a user
 *        (e.g. immediately after a successful login flow).
 */
import { useEffect } from "react";
import { useSession } from "@/stores/session";
import {
  getAccessToken,
  refreshAccessToken,
  setAccessToken,
  onAuthChange,
} from "@/lib/auth/session";
import { getMe } from "@/lib/api/users";

export function useSessionBootstrap(): ReturnType<typeof useSession.getState> {
  const state = useSession();
  const setUser = useSession((s) => s.setUser);
  const setStatus = useSession((s) => s.setStatus);

  useEffect(() => {
    // Already populated (e.g. just logged in)? Don't re-bootstrap.
    if (useSession.getState().status === "authenticated") return;

    (async () => {
      setStatus("loading");
      try {
        let token = getAccessToken();
        if (!token) token = await refreshAccessToken();
        if (!token) {
          setUser(null);
          return;
        }
        const user = await getMe();
        setUser(user);
      } catch {
        setAccessToken(null);
        setUser(null);
      }
    })();

    const off = onAuthChange((tok) => {
      if (!tok) useSession.getState().reset();
    });

    return () => {
      off();
    };
  }, [setUser, setStatus]);

  return state;
}
