"use client";
/**
 * @file components/chat/chat-layout/useDetails.ts
 * @brief Details panel state. At xl+ it is an inline column, open by default
 *        and remembered (localStorage `nexara.chat.details`); below xl it is
 *        a slide-over that starts closed.
 */
import * as React from "react";

export const DETAILS_KEY = "nexara.chat.details";
const XL = "(min-width: 1280px)";

function subscribe(cb: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => {};
  const mq = window.matchMedia(XL);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}

/** @brief True at the xl breakpoint (false on the server). */
export function useIsXl(): boolean {
  return React.useSyncExternalStore(
    subscribe,
    () =>
      typeof window.matchMedia === "function" && window.matchMedia(XL).matches,
    () => false,
  );
}

/** @brief Saved inline preference, or null when never set. */
export function readDetailsPref(): boolean | null {
  try {
    const v = window.localStorage.getItem(DETAILS_KEY);
    return v === "open" ? true : v === "closed" ? false : null;
  } catch {
    return null;
  }
}

/**
 * @return `{ open, inline, toggle, close }`; `inline` is true at xl+.
 */
export function useDetails() {
  const inline = useIsXl();
  const [pref, setPref] = React.useState<boolean | null>(null);
  const [sheet, setSheet] = React.useState(false);
  React.useEffect(() => setPref(readDetailsPref()), []);
  const open = inline ? (pref ?? true) : sheet;
  const toggle = React.useCallback(() => {
    if (inline) {
      const next = !(pref ?? true);
      setPref(next);
      try {
        window.localStorage.setItem(DETAILS_KEY, next ? "open" : "closed");
      } catch {
        /* storage unavailable */
      }
    } else setSheet((s) => !s);
  }, [inline, pref]);
  const close = React.useCallback(() => setSheet(false), []);
  return { open, inline, toggle, close };
}
