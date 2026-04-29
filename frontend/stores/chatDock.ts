/**
 * @file stores/chatDock.ts
 * @brief Floating mini-chat dock state. Tracks open thread ids, minimized
 *        state per thread, launcher visibility, and unread count.
 *        openThreadIds is persisted to sessionStorage (survives refresh but
 *        not new tabs / sessions).
 */
import { create } from "zustand";

const SESSION_KEY = "chatDock.openThreadIds";
const MAX_THREADS = 3;

function loadFromSession(): string[] {
  if (typeof sessionStorage === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as string[]) : [];
  } catch {
    return [];
  }
}

function saveToSession(ids: string[]): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(ids));
}

export interface ChatDockState {
  openThreadIds: string[];
  minimized: Record<string, boolean>;
  launcherOpen: boolean;
  unreadCount: number;

  openThread(id: string): void;
  closeThread(id: string): void;
  toggleMinimize(id: string): void;
  setLauncherOpen(open: boolean): void;
  setUnreadCount(n: number): void;
}

export const useChatDock = create<ChatDockState>((set) => ({
  openThreadIds: loadFromSession(),
  minimized: {},
  launcherOpen: false,
  unreadCount: 0,

  openThread: (id) =>
    set((s) => {
      if (s.openThreadIds.includes(id)) return s;
      const next = [...s.openThreadIds, id];
      // Cap at MAX_THREADS — evict from front (oldest)
      const capped =
        next.length > MAX_THREADS
          ? next.slice(next.length - MAX_THREADS)
          : next;
      saveToSession(capped);
      return { openThreadIds: capped };
    }),

  closeThread: (id) =>
    set((s) => {
      const next = s.openThreadIds.filter((t) => t !== id);
      saveToSession(next);
      const minimized = { ...s.minimized };
      delete minimized[id];
      return { openThreadIds: next, minimized };
    }),

  toggleMinimize: (id) =>
    set((s) => ({
      minimized: { ...s.minimized, [id]: !s.minimized[id] },
    })),

  setLauncherOpen: (open) => set({ launcherOpen: open }),

  setUnreadCount: (n) => set({ unreadCount: n }),
}));
