"use client";
/**
 * @file components/layout/SwNavigateBridge.tsx
 * @brief Routes service-worker {type:"navigate",url} messages (notification
 *        clicks) through the Next router. Renders nothing.
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { safePath } from "@/lib/notifications/pushTag";

/** @brief Mount once in the authenticated shell. @return null */
export function SwNavigateBridge() {
  const router = useRouter();
  useEffect(() => {
    const sw = navigator.serviceWorker;
    if (!sw) return;
    const on = (e: MessageEvent) => {
      const d = e.data as { type?: string; url?: string } | null;
      const url = safePath(d?.url);
      if (d?.type === "navigate" && url) router.push(url);
    };
    sw.addEventListener("message", on);
    return () => sw.removeEventListener("message", on);
  }, [router]);
  return null;
}
