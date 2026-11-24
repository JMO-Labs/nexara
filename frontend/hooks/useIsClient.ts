/**
 * @file hooks/useIsClient.ts
 * @brief False during SSR and hydration, true afterwards (avoids mismatches
 *        for browser-only checks such as window.isSecureContext).
 */
import { useSyncExternalStore } from "react";

const noop = () => () => {};

/** @return true once running in the browser after hydration */
export function useIsClient(): boolean {
  return useSyncExternalStore(
    noop,
    () => true,
    () => false,
  );
}
