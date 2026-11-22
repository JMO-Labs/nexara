"use client";
/**
 * @file components/ui/Toast.tsx
 * @brief ToastRoot renders the useToasts store in a polite live region.
 *        On-brand glass cards with an icon disc per kind.
 */
import { useEffect } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Loader2,
  X,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  useToasts,
  selectVisible,
  type Toast as ToastT,
  type ToastVariant,
} from "@/stores/toasts";

const TONE: Record<ToastVariant, { color: string; Icon: LucideIcon }> = {
  info: { color: "var(--nx-accent)", Icon: Info },
  success: { color: "var(--nx-ok)", Icon: CheckCircle2 },
  warning: { color: "var(--nx-sun)", Icon: AlertTriangle },
  danger: { color: "var(--nx-danger)", Icon: XCircle },
  loading: { color: "var(--nx-accent)", Icon: Loader2 },
};

function ToastItem({ toast }: { toast: ToastT }) {
  const dismiss = useToasts((s) => s.dismiss);
  const reduce = useReducedMotion();
  const tone = TONE[toast.variant];
  useEffect(() => {
    if (!toast.ttl) return;
    const t = setTimeout(() => dismiss(toast.id), toast.ttl);
    return () => clearTimeout(t);
  }, [toast.id, toast.ttl, dismiss]);

  return (
    <motion.div
      layout={!reduce}
      initial={{ opacity: 0, y: reduce ? 0 : 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: reduce ? 0 : 8 }}
      transition={{ duration: reduce ? 0 : 0.18 }}
      aria-live={toast.variant === "danger" ? "assertive" : "polite"}
      className="flex w-full max-w-sm items-center gap-3 rounded-[22px] border border-[var(--nx-glass-edge)] bg-[color-mix(in_srgb,var(--nx-glass-solid)_88%,transparent)] p-2.5 pr-2 text-ink shadow-[0_18px_40px_-16px_rgba(0,0,0,0.5)] backdrop-blur-xl"
    >
      <span
        aria-hidden
        className="grid size-9 shrink-0 place-items-center rounded-full"
        style={{
          color: tone.color,
          background: `color-mix(in srgb, ${tone.color} 16%, transparent)`,
        }}
      >
        <tone.Icon
          className={cn(
            "size-[18px]",
            toast.variant === "loading" &&
              "animate-spin motion-reduce:animate-none",
          )}
        />
      </span>
      <div className="min-w-0 flex-1">
        {toast.title ? <p className="font-semibold">{toast.title}</p> : null}
        <p className="text-sm">{toast.message}</p>
      </div>
      {toast.action ? (
        <button
          type="button"
          onClick={toast.action.onClick}
          className="text-accent focus-visible:outline-accent rounded-full px-3 py-1.5 text-sm font-semibold hover:bg-[color-mix(in_srgb,var(--nx-ink)_7%,transparent)] focus-visible:outline-2 focus-visible:outline-offset-2"
        >
          {toast.action.label}
        </button>
      ) : null}
      <button
        type="button"
        aria-label="Dismiss"
        onClick={() => dismiss(toast.id)}
        className="focus-visible:outline-accent grid size-8 place-items-center rounded-full text-muted hover:bg-[color-mix(in_srgb,var(--nx-ink)_7%,transparent)] focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        <X className="size-4" aria-hidden />
      </button>
    </motion.div>
  );
}

/**
 * @brief Toast region; bottom-center above tab bar on phones, bottom-right >= md.
 * @return live region element
 */
export function ToastRoot() {
  const items = selectVisible(useToasts((s) => s.items));
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Notifications"
      className="pointer-events-none fixed inset-x-0 bottom-[calc(84px+env(safe-area-inset-bottom))] z-[100] flex flex-col items-center gap-2 px-3 md:inset-x-auto md:right-4 md:bottom-4 md:items-end [&>*]:pointer-events-auto"
    >
      <AnimatePresence initial={false}>
        {items.map((t) => (
          <ToastItem key={t.id} toast={t} />
        ))}
      </AnimatePresence>
    </div>
  );
}

export default ToastRoot;
