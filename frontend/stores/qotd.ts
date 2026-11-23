/**
 * @file stores/qotd.ts
 * @brief Answered status of questions of the day + quick-nav open event.
 */
import { create } from "zustand";

export const OPEN_QOTD_EVENT = "nexara:open-qotd";

interface QotdState {
  /** prompt post id -> answered (absent until known). */
  answered: Record<string, boolean>;
  /** Ids currently shown by the stack; null when no stack is mounted. */
  ids: string[] | null;
  setAnswered: (id: string, v: boolean) => void;
  setIds: (ids: string[] | null) => void;
}

export const useQotd = create<QotdState>()((set) => ({
  answered: {},
  ids: null,
  setAnswered: (id, v) =>
    set((s) =>
      s.answered[id] === v ? s : { answered: { ...s.answered, [id]: v } },
    ),
  setIds: (ids) => set({ ids }),
}));

/**
 * @brief Ids of known-unanswered questions, or null if no stack is mounted.
 * @param s store state
 * @return unanswered ids in stack order, or null
 */
export const selectUnanswered = (s: QotdState): string[] | null =>
  s.ids ? s.ids.filter((id) => s.answered[id] === false) : null;

/** @brief Ask the stack to open the first unanswered question. */
export function openFirstUnanswered(): void {
  window.dispatchEvent(new CustomEvent(OPEN_QOTD_EVENT));
}
