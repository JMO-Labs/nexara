"use client";
/**
 * @file components/layout/InstallPrompt.tsx
 * @brief PWA install affordance. `card` (More sheet) and `banner` (one-time,
 *        after the 3rd visit). iOS Safari gets manual Add-to-Home-Screen steps.
 *        Hidden when already running standalone.
 */
import { useEffect, useState } from "react";
import { Button } from "@/components/ui";
import { Drawer } from "@/components/ui/Drawer";

interface InstallEvent extends Event {
  prompt: () => Promise<void>;
}

let deferred: InstallEvent | null = null;
const subs = new Set<() => void>();
if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferred = e as InstallEvent;
    subs.forEach((f) => f());
  });
}

function store(op: "get" | "set", key: string, val = ""): string | null {
  try {
    if (op === "set") localStorage.setItem(key, val);
    else return localStorage.getItem(key);
  } catch {
    /* storage blocked */
  }
  return null;
}

export function standalone(): boolean {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    (navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

/** @brief Any iOS browser (incl. iPadOS reporting a Mac UA with touch). */
export function isIos(): boolean {
  const ua = navigator.userAgent;
  return (
    /iPad|iPhone|iPod/.test(ua) ||
    (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)
  );
}

/**
 * @brief Install prompt.
 * @param variant "card" always shown until dismissed; "banner" after 3rd visit
 * @return element or null
 */
export function InstallPrompt({ variant }: { variant: "card" | "banner" }) {
  const [, tick] = useState(0);
  const [ready, setReady] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [steps, setSteps] = useState(false);
  const key = `nx:install-${variant}-dismissed`;

  useEffect(() => {
    const f = () => tick((n) => n + 1);
    subs.add(f);
    if (store("get", key)) setDismissed(true);
    if (variant === "banner") {
      try {
        if (!sessionStorage.getItem("nx:visit")) {
          sessionStorage.setItem("nx:visit", "1");
          const n = Number(store("get", "nx:visits") ?? 0) + 1;
          store("set", "nx:visits", String(n));
        }
      } catch {
        /* ignore */
      }
      if (Number(store("get", "nx:visits") ?? 0) < 3) setDismissed(true);
    }
    setReady(true);
    return () => void subs.delete(f);
  }, [key, variant]);

  if (!ready || dismissed || standalone()) return null;
  const ios = isIos();
  if (!ios && !deferred) return null;

  const dismiss = () => {
    store("set", key, "1");
    setDismissed(true);
  };
  const install = async () => {
    if (ios) return setSteps(true);
    await deferred?.prompt();
    deferred = null;
    dismiss();
  };
  return (
    <div
      role="region"
      aria-label="Install app"
      className="glass-item m-3 flex items-center gap-3 rounded-[20px] p-3 text-sm"
    >
      <span className="flex-1">Install Nexara for quick access.</span>
      <Button size="sm" onClick={install}>
        {ios ? "How to install" : "Install"}
      </Button>
      <Button size="sm" variant="ghost" onClick={dismiss}>
        Dismiss
      </Button>
      <Drawer
        open={steps}
        onClose={() => setSteps(false)}
        title="Install"
        side="bottom"
      >
        <p className="p-4">Tap Share, then Add to Home Screen.</p>
      </Drawer>
    </div>
  );
}
