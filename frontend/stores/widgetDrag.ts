/**
 * @file stores/widgetDrag.ts
 * @brief Tracks widget instance IDs that have requested drag be disabled
 *        (e.g. UpcomingEventsWidget while a detail panel is open).
 */
import { create } from "zustand";

interface WidgetDragState {
  disabledIds: Set<string>;
  disable: (id: string) => void;
  enable: (id: string) => void;
}

export const useWidgetDrag = create<WidgetDragState>((set) => ({
  disabledIds: new Set(),
  disable: (id) =>
    set((s) => ({ disabledIds: new Set([...s.disabledIds, id]) })),
  enable: (id) =>
    set((s) => {
      const next = new Set(s.disabledIds);
      next.delete(id);
      return { disabledIds: next };
    }),
}));
