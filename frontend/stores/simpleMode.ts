"use client";
/**
 * @file stores/simpleMode.ts
 * @brief Whether simple mode is active for the viewer (setting on AND the
 *        community feature flag on). Written by SimpleModeSync, read by nav.
 */
import { create } from "zustand";

interface SimpleModeState {
  on: boolean;
  setOn: (on: boolean) => void;
}

export const useSimpleMode = create<SimpleModeState>((set) => ({
  on: false,
  setOn: (on) => set({ on }),
}));
