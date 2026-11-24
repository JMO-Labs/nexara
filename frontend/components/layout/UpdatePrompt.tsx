"use client";
/**
 * @file components/layout/UpdatePrompt.tsx
 * @brief Toasts "New version available" when a service worker is waiting;
 *        Reload posts SKIP_WAITING and reloads on controllerchange.
 */
import { useEffect } from "react";
import { useToasts } from "@/stores/toasts";

/** @brief Mount once. @return null */
export default function UpdatePrompt() {
  const push = useToasts((s) => s.push);
  useEffect(() => {
    const sw =
      typeof navigator !== "undefined" ? navigator.serviceWorker : undefined;
    if (!sw?.getRegistration) return;
    let shown = false;
    let reloading = false;
    const show = (worker: ServiceWorker) => {
      if (shown) return;
      shown = true;
      push({
        variant: "info",
        message: "New version available",
        ttl: null,
        dedupeKey: "sw-update",
        action: {
          label: "Reload",
          onClick: () => {
            if (reloading) return;
            reloading = true;
            sw.addEventListener(
              "controllerchange",
              () => window.location.reload(),
              { once: true },
            );
            worker.postMessage({ type: "SKIP_WAITING" });
          },
        },
      });
    };
    const watch = (reg: ServiceWorkerRegistration) => {
      if (reg.waiting) show(reg.waiting);
      reg.addEventListener("updatefound", () => {
        const w = reg.installing;
        w?.addEventListener("statechange", () => {
          if (w.state === "installed" && sw.controller) show(w);
        });
      });
    };
    sw.getRegistration()
      .then((r) => r && watch(r))
      .catch(() => {});
  }, [push]);
  return null;
}
