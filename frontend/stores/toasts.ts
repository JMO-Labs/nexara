/**
 * @file stores/toasts.ts
 * @brief Toast queue. Components call push(); ToastRoot subscribes and
 *        renders. ARIA live region wired in the renderer (Phase 1).
 */
import { create } from "zustand";

export type ToastVariant =
  | "info"
  | "success"
  | "warning"
  | "danger"
  | "loading";

export interface Toast {
  id: string;
  variant: ToastVariant;
  title?: string;
  message: string;
  ttl?: number | null;
}

interface ToastsState {
  items: Toast[];
  push: (t: Omit<Toast, "id">) => string;
  dismiss: (id: string) => void;
  update: (id: string, partial: Partial<Omit<Toast, "id">>) => void;
  clear: () => void;
}

const getDefaultTtl = (variant: ToastVariant): number | null => {
  switch (variant) {
    case "success":
      return 4000;
    case "danger":
      return 6000;
    case "info":
      return 4000;
    case "warning":
      return 4000;
    case "loading":
      return null;
    default:
      return 4500;
  }
};

/** Max toasts rendered at once; the rest stay queued. */
export const MAX_VISIBLE_TOASTS = 3;

/**
 * @brief First MAX_VISIBLE_TOASTS items.
 * @param items full queue
 * @return visible slice
 */
export const selectVisible = (items: Toast[]): Toast[] =>
  items.slice(0, MAX_VISIBLE_TOASTS);

export const useToasts = create<ToastsState>((set) => ({
  items: [],
  push: (t) => {
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `t_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const ttl = t.ttl !== undefined ? t.ttl : getDefaultTtl(t.variant);
    set((s) => ({ items: [...s.items, { ...t, id, ttl }] }));
    return id;
  },
  dismiss: (id) => set((s) => ({ items: s.items.filter((x) => x.id !== id) })),
  update: (id, partial) =>
    set((s) => ({
      items: s.items.map((x) => {
        if (x.id !== id) return x;
        const next = { ...x, ...partial };
        if (partial.variant && partial.ttl === undefined) {
          next.ttl = getDefaultTtl(partial.variant);
        }
        return next;
      }),
    })),
  clear: () => set({ items: [] }),
}));
