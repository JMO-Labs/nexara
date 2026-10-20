/**
 * @file stores/session.ts
 * @brief Authenticated user + auth lifecycle state. Server data (profile
 *        details that change frequently) lives in TanStack Query; this
 *        store carries the identity scaffolding the whole shell depends on.
 */
import { create } from "zustand";
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

export const useSession = create<SessionState>((set) => ({
  status: "idle",
  user: null,
  setUser: (user) =>
    set({ user, status: user ? "authenticated" : "unauthenticated" }),
  setStatus: (status) => set({ status }),
  reset: () => set({ user: null, status: "unauthenticated" }),
}));
