/**
 * @file stores/dashboardRail.ts
 * @brief Right-rail tab state. Currently tracks the customize drawer; chat
 *        drawer state lives in stores/chatDock.ts (launcherOpen).
 */
import { create } from "zustand";

interface DashboardRailState {
  customizeOpen: boolean;
  setCustomizeOpen: (open: boolean) => void;
}

export const useDashboardRail = create<DashboardRailState>((set) => ({
  customizeOpen: false,
  setCustomizeOpen: (open) => set({ customizeOpen: open }),
}));
