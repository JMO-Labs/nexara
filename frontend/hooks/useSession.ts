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
  refreshSession,
  setAccessToken,
  onAuthChange,
} from "@/lib/auth/session";
import { loadLastUser } from "@/lib/auth/lastUser";
import { ApiError } from "@/lib/api/errors";
import { getMe } from "@/lib/api/users";

export function useSessionBootstrap(): ReturnType<typeof useSession.getState> {
  const state = useSession();
  const setUser = useSession((s) => s.setUser);
  const setStatus = useSession((s) => s.setStatus);

  useEffect(() => {
    // Already populated (e.g. just logged in)? Don't re-bootstrap.
    if (useSession.getState().status === "authenticated") return;

    let cancelled = false;
    // Network trouble is never a sign-out: boot from the last user (offline
    // shell + their persisted cache) or wait for connectivity and retry.
    const offline = () => {
      const last = loadLastUser();
      if (last) setUser(last);
      else window.addEventListener("online", boot, { once: true });
    };
    async function boot() {
      if (cancelled) return;
      setStatus("loading");
      try {
        let token = getAccessToken();
        if (!token) {
          const r = await refreshSession();
          if (r.transient) return offline();
          token = r.token;
        }
        if (!token) {
          setUser(null);
          return;
        }
        const user = await getMe();
        setUser(user);
      } catch (err) {
        if (
          err instanceof ApiError &&
          (err.status === 401 || err.status === 403)
        ) {
          setAccessToken(null);
          setUser(null);
        } else offline();
      }
    }
    void boot();

    const off = onAuthChange((tok) => {
      if (!tok) useSession.getState().reset();
    });

    return () => {
      cancelled = true;
      window.removeEventListener("online", boot);
      off();
    };
  }, [setUser, setStatus]);

  return state;
}
