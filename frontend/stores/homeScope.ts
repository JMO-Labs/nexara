/**
 * @file stores/homeScope.ts
 * @brief Home scope filter (Everything or one group); not persisted.
 */
import { create } from "zustand";

interface HomeScopeState {
  scope: string | "all";
  setScope: (s: string | "all") => void;
}

export const useHomeScope = create<HomeScopeState>()((set) => ({
  scope: "all",
  setScope: (scope) => set({ scope }),
}));

/**
 * @brief Whether an item in the given group passes the scope filter.
 * @param subgroupId Item's group id, or null when community-wide.
 * @param scope Active scope ("all" or a group id).
 * @return true when visible
 */
export function inScope(subgroupId: string | null, scope: string): boolean {
  return scope === "all" || subgroupId === scope;
}
