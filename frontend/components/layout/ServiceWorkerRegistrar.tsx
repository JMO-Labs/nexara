"use client";
/**
 * @file components/layout/ServiceWorkerRegistrar.tsx
 * @brief Mounts once at the app shell to register /sw.js after first paint.
 *        Production-only: dev SW would interfere with Turbopack HMR.
 */
import { useEffect } from "react";

export default function ServiceWorkerRegistrar() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (typeof window === "undefined" || !("serviceWorker" in navigator))
      return;
    const onLoad = () => {
      navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .catch((err) => console.error("[sw] registration failed", err));
    };
    if (document.readyState === "complete") onLoad();
    else window.addEventListener("load", onLoad, { once: true });
    return () => window.removeEventListener("load", onLoad);
  }, []);
  return null;
}
