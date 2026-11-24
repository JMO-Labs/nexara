/**
 * @file stores/session.ts
 * @brief Authenticated user + auth lifecycle state. Server data (profile
 *        details that change frequently) lives in TanStack Query; this
 *        store carries the identity scaffolding the whole shell depends on.
 */
import { create } from "zustand";
import { clearUserCache } from "@/lib/pwa/clearUserCache";
import { clearLastUser, saveLastUser } from "@/lib/auth/lastUser";
import type { CurrentUser } from "@/lib/api/users";

export type SessionStatus =
  | "idle"
  | "loading"
  | "authenticated"
  | "unauthenticated";

interface SessionState {
  status: SessionStatus;
  user: CurrentUser | null;
  setUser: (user: CurrentUser | null) => void;
  setStatus: (status: SessionStatus) => void;
  reset: () => void;
}

export const useSession = create<SessionState>((set, get) => ({
  status: "idle",
  user: null,
  setUser: (user) => {
    // Sign-out (incl. forced 401) or account switch: purge saved pages.
    const prev = get().user;
    if (!user ? prev : prev && prev.id !== user.id) clearUserCache();
    if (user) saveLastUser(user);
    else clearLastUser();
    set({ user, status: user ? "authenticated" : "unauthenticated" });
  },
  setStatus: (status) => set({ status }),
  reset: () => {
    clearUserCache();
    clearLastUser();
    set({ user: null, status: "unauthenticated" });
  },
}));
