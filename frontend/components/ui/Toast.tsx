"use client";
/**
 * @file components/ui/Toast.tsx
 * @brief ToastRoot renders the useToasts store in a polite live region.
 */
import { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useToasts,
  type Toast as ToastT,
  type ToastVariant,
} from "@/stores/toasts";

const TONE: Record<ToastVariant, string> = {
  info: "border-muted/40",
  success: "border-leaf",
  warning: "border-sun",
  danger: "border-red-600",
  loading: "border-accent",
};

function ToastItem({ toast }: { toast: ToastT }) {
  const dismiss = useToasts((s) => s.dismiss);
  useEffect(() => {
    if (!toast.ttl) return;
    const t = setTimeout(() => dismiss(toast.id), toast.ttl);
    return () => clearTimeout(t);
  }, [toast.id, toast.ttl, dismiss]);

  return (
    <div
      className={cn(
        "bg-surface text-ink flex w-full max-w-sm items-start gap-3 rounded-2xl border-l-4 p-3 shadow-lg",
        TONE[toast.variant],
      )}
    >
      <div className="min-w-0 flex-1">
        {toast.title ? <p className="font-semibold">{toast.title}</p> : null}
        <p className="text-sm">{toast.message}</p>
      </div>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={() => dismiss(toast.id)}
        className="focus-visible:outline-accent rounded p-1 focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        <X className="size-4" aria-hidden />
      </button>
    </div>
  );
}

/**
 * @brief Toast region; bottom-center above tab bar on phones, bottom-right >= md.
 * @return live region element
 */
export function ToastRoot() {
  const items = useToasts((s) => s.items).slice(0, 3);
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Notifications"
      className="pointer-events-none fixed inset-x-0 bottom-[calc(84px+env(safe-area-inset-bottom))] z-[100] flex flex-col items-center gap-2 px-3 md:inset-x-auto md:right-4 md:bottom-4 md:items-end [&>*]:pointer-events-auto"
    >
      {items.map((t) => (
        <ToastItem key={t.id} toast={t} />
      ))}
    </div>
  );
}

export default ToastRoot;
