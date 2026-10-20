"use client";
/**
 * @file hooks/useIsMobile.ts
 * @brief Returns true when viewport width is < 768px (mobile breakpoint).
 *        Initialises to false to avoid SSR/hydration mismatch.
 */
import * as React from "react";

export function useIsMobile(): boolean {
  const [mobile, setMobile] = React.useState(false);
  React.useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const handler = (e: MediaQueryListEvent) => setMobile(e.matches);
    // Sync initial value after mount (avoids synchronous setState-in-effect lint)
    handler({ matches: mq.matches } as MediaQueryListEvent);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return mobile;
}
