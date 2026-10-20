/**
 * @file stores/branding.ts
 * @brief Runtime branding (name, logo) for layout chrome. Written by
 *        BrandingStyle; read by SideNav/TopBar without a query provider.
 */
import { create } from "zustand";

interface BrandingState {
  name: string;
  logoUrl: string | null;
  set: (name: string, logoUrl: string | null) => void;
}

export const useBrandingStore = create<BrandingState>((set) => ({
  name: "Nexara",
  logoUrl: null,
  set: (name, logoUrl) => set({ name, logoUrl }),
}));
