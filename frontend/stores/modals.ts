/**
 * @file stores/modals.ts
 * @brief Imperative modal/drawer registry. URL-driven modals (post drawer,
 *        gallery lightbox) live as intercepting routes; this store covers
 *        ephemeral confirms, composers, and forms triggered from buttons.
 */
import { create } from "zustand";

export type ModalKey =
  | "create-post"
  | "create-event"
  | "create-gallery"
  | "create-subgroup"
  | "invite-member"
  | "confirm";

interface ModalState {
  open: ModalKey | null;
  payload: unknown;
  show: (key: ModalKey, payload?: unknown) => void;
  close: () => void;
  keyboardShortcutsOpen: boolean;
  setKeyboardShortcutsOpen: (open: boolean) => void;
}

export const useModals = create<ModalState>((set) => ({
  open: null,
  payload: undefined,
  show: (key, payload) => set({ open: key, payload }),
  close: () => set({ open: null, payload: undefined }),
  keyboardShortcutsOpen: false,
  setKeyboardShortcutsOpen: (open) => set({ keyboardShortcutsOpen: open }),
}));
