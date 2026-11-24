/**
 * @file stores/pendingTwoFactor.ts
 * @brief In-memory handoff of a pending 2FA login (token + methods) so the
 *        token never rides in the URL or browser history.
 */
import { create } from "zustand";

interface PendingTwoFactor {
  token: string | null;
  methods: string[];
  set: (token: string, methods: string[]) => void;
  clear: () => void;
}

export const usePendingTwoFactor = create<PendingTwoFactor>((set) => ({
  token: null,
  methods: [],
  set: (token, methods) => set({ token, methods }),
  clear: () => set({ token: null, methods: [] }),
}));
