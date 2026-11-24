"use client";
/**
 * @file components/layout/OfflineBanner.tsx
 * @brief Top banner shown while offline (pages served from the SW cache).
 */
import { useOnline } from "@/hooks/useOnline";

/** @brief Offline notice. @return banner or null when online */
export function OfflineBanner() {
  if (useOnline()) return null;
  return (
    <div
      role="status"
      className="bg-surface-strong text-bg px-4 py-2 text-center text-sm print:hidden"
    >
      You&apos;re offline. Showing saved pages.
    </div>
  );
}
