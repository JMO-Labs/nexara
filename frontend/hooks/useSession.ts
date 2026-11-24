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

/** Backoff between boot retries while online but the server is failing. */
const RETRY_MS = [2_000, 5_000, 15_000, 30_000];

export function useSessionBootstrap(): ReturnType<typeof useSession.getState> {
  const state = useSession();
  const setUser = useSession((s) => s.setUser);
  const setStatus = useSession((s) => s.setStatus);

  useEffect(() => {
    // Already populated (e.g. just logged in)? Don't re-bootstrap.
    if (useSession.getState().status === "authenticated") return;

    let cancelled = false;
    let running = false;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const retry = () => {
      clearTimeout(timer);
      void boot();
    };
    const onVisible = () => {
      if (document.visibilityState === "visible") retry();
    };
    const stopRetry = () => {
      clearTimeout(timer);
      window.removeEventListener("online", retry);
      document.removeEventListener("visibilitychange", onVisible);
    };
    // Network trouble is never a sign-out: boot from the last user (offline
    // shell + their persisted cache) or retry: on `online`, when the app is
    // shown again, and with backoff while the browser says it is online
    // (5xx/429 from a reachable server never fires `online`).
    const offline = () => {
      const last = loadLastUser();
      if (last) {
        // Not setUser: re-saving would extend the snapshot's 24h lifetime.
        useSession.setState({ user: last, status: "authenticated" });
        return;
      }
      window.addEventListener("online", retry);
      document.addEventListener("visibilitychange", onVisible);
      if (navigator.onLine)
        timer = setTimeout(
          retry,
          RETRY_MS[Math.min(attempt++, RETRY_MS.length - 1)],
        );
    };
    async function boot() {
      if (cancelled || running) return;
      running = true;
      setStatus("loading");
      try {
        let token = getAccessToken();
        if (!token) {
          const r = await refreshSession();
          if (r.transient) return offline();
          token = r.token;
        }
        stopRetry();
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
      } finally {
        running = false;
      }
    }
    void boot();

    const off = onAuthChange((tok) => {
      if (!tok) useSession.getState().reset();
    });

    return () => {
      cancelled = true;
      stopRetry();
      off();
    };
  }, [setUser, setStatus]);

  return state;
}
