/**
 * @file stores/ui.ts
 * @brief Layout/UI client state — density, command palette.
 *        Server data lives in TanStack Query, never here.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  density: "comfortable" | "compact";
  commandPaletteOpen: boolean;
  chatToastsMuted: boolean;
  setDensity: (d: UIState["density"]) => void;
  setCommandPaletteOpen: (v: boolean) => void;
  setChatToastsMuted: (v: boolean) => void;
  toggleChatToastsMuted: () => void;
}

export const useUI = create<UIState>()(
  persist(
    (set) => ({
      density: "comfortable",
      commandPaletteOpen: false,
      chatToastsMuted: false,
      setDensity: (d) => set({ density: d }),
      setCommandPaletteOpen: (v) => set({ commandPaletteOpen: v }),
      setChatToastsMuted: (v) => set({ chatToastsMuted: v }),
      toggleChatToastsMuted: () =>
        set((s) => ({ chatToastsMuted: !s.chatToastsMuted })),
    }),
    {
      name: "nx-ui",
      partialize: (s) => ({
        density: s.density,
        chatToastsMuted: s.chatToastsMuted,
      }),
    },
  ),
);
