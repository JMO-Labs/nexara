/**
 * @file stores/ui.ts
 * @brief Layout/UI client state — sidebar, density, command palette.
 *        Server data lives in TanStack Query, never here.
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  sidebarCollapsed: boolean;
  density: "comfortable" | "compact";
  commandPaletteOpen: boolean;
  chatToastsMuted: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (v: boolean) => void;
  setDensity: (d: UIState["density"]) => void;
  setCommandPaletteOpen: (v: boolean) => void;
  setChatToastsMuted: (v: boolean) => void;
  toggleChatToastsMuted: () => void;
}

export const useUI = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      density: "comfortable",
      commandPaletteOpen: false,
      chatToastsMuted: false,
      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
      setDensity: (d) => set({ density: d }),
      setCommandPaletteOpen: (v) => set({ commandPaletteOpen: v }),
      setChatToastsMuted: (v) => set({ chatToastsMuted: v }),
      toggleChatToastsMuted: () =>
        set((s) => ({ chatToastsMuted: !s.chatToastsMuted })),
    }),
    {
      name: "nx-ui",
      partialize: (s) => ({
        sidebarCollapsed: s.sidebarCollapsed,
        density: s.density,
        chatToastsMuted: s.chatToastsMuted,
      }),
    },
  ),
);
