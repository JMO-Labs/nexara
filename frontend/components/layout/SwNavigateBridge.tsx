"use client";
/**
 * @file components/layout/SwNavigateBridge.tsx
 * @brief Routes service-worker {type:"navigate",url} messages (notification
 *        clicks) through the Next router. Renders nothing.
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** @brief Mount once in the authenticated shell. @return null */
export function SwNavigateBridge() {
  const router = useRouter();
  useEffect(() => {
    const sw = navigator.serviceWorker;
    if (!sw) return;
    const on = (e: MessageEvent) => {
      const d = e.data as { type?: string; url?: string } | null;
      if (d?.type === "navigate" && d.url?.startsWith("/")) router.push(d.url);
    };
    sw.addEventListener("message", on);
    return () => sw.removeEventListener("message", on);
  }, [router]);
  return null;
}
