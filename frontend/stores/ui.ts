/**
 * @file stores/ui.ts
 * @brief Layout/UI client state — sidebar, density, command palette.
 *        Server data lives in TanStack Query, never here.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  sidebarCollapsed: boolean;
  density: 'comfortable' | 'compact';
  commandPaletteOpen: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (v: boolean) => void;
  setDensity: (d: UIState['density']) => void;
  setCommandPaletteOpen: (v: boolean) => void;
}

export const useUI = create<UIState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      density: 'comfortable',
      commandPaletteOpen: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),
      setDensity: (d) => set({ density: d }),
      setCommandPaletteOpen: (v) => set({ commandPaletteOpen: v }),
    }),
    { name: 'nx-ui', partialize: (s) => ({ sidebarCollapsed: s.sidebarCollapsed, density: s.density }) },
  ),
);
