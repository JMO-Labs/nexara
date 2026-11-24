"use client";
/**
 * @file hooks/useAppBadge.ts
 * @brief Mirrors the unread count onto the installed app icon badge.
 */
import { useEffect } from "react";

/** @param unread unread notification count; 0 clears the badge */
export function useAppBadge(unread: number): void {
  useEffect(() => {
    const nav = navigator as Navigator & {
      setAppBadge?: (n: number) => Promise<void>;
      clearAppBadge?: () => Promise<void>;
    };
    const p = unread > 0 ? nav.setAppBadge?.(unread) : nav.clearAppBadge?.();
    p?.catch(() => {});
  }, [unread]);
}
