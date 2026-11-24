"use client";
/**
 * @file hooks/useOnline.ts
 * @brief Reactive navigator.onLine (SSR-safe: assumes online).
 */
import { useSyncExternalStore } from "react";

function subscribe(cb: () => void) {
  window.addEventListener("online", cb);
  window.addEventListener("offline", cb);
  return () => {
    window.removeEventListener("online", cb);
    window.removeEventListener("offline", cb);
  };
}

/** @brief True while the browser reports a network connection. @return boolean */
export function useOnline(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => navigator.onLine,
    () => true,
  );
}
