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

/** @brief Optional action button rendered inside a toast. */
export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface Toast {
  id: string;
  variant: ToastVariant;
  title?: string;
  message: string;
  ttl?: number | null;
  action?: ToastAction;
  /** Higher sorts first. */
  priority?: number;
  /** Pushes with the same key inside 5s return the existing toast id. */
  dedupeKey?: string;
}

const DEDUPE_WINDOW_MS = 5000;
const _recent = new Map<string, { id: string; at: number }>();

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
    if (t.dedupeKey) {
      const seen = _recent.get(t.dedupeKey);
      if (seen && Date.now() - seen.at < DEDUPE_WINDOW_MS) return seen.id;
    }
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `t_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const ttl = t.ttl !== undefined ? t.ttl : getDefaultTtl(t.variant);
    if (t.dedupeKey) _recent.set(t.dedupeKey, { id, at: Date.now() });
    set((s) => ({
      items: [...s.items, { ...t, id, ttl }].sort(
        (a, b) => (b.priority ?? 0) - (a.priority ?? 0),
      ),
    }));
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
  clear: () => {
    _recent.clear();
    set({ items: [] });
  },
}));
