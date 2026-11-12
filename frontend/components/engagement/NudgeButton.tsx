"use client";
/**
 * @file components/engagement/NudgeButton.tsx
 * @brief Button to nudge a member; 24h cooldown with "Nudged 4h ago" label.
 */
import { useCallback, useEffect, useState } from "react";
import { Hand } from "lucide-react";
import { sendNudge } from "@/lib/api/nudges";
import { ApiError } from "@/lib/api/errors";
import { useToasts } from "@/stores/toasts";

const COOLDOWN_MS = 24 * 3600_000;
const key = (id: string) => `nudge:${id}`;

/**
 * @brief Human label for time elapsed since the last nudge.
 * @param elapsedMs milliseconds since nudge
 * @return e.g. "Nudged 4h ago"
 */
export function formatCooldown(elapsedMs: number): string {
  const mins = Math.floor(elapsedMs / 60_000);
  if (mins < 1) return "Nudged just now";
  if (mins < 60) return `Nudged ${mins}m ago`;
  return `Nudged ${Math.floor(mins / 60)}h ago`;
}

function readStored(id: string): number | null {
  try {
    const v = Number(localStorage.getItem(key(id)));
    return v && Date.now() - v < COOLDOWN_MS ? v : null;
  } catch {
    return null;
  }
}

/**
 * @brief Nudge button with cooldown state.
 * @param userId target user id
 * @return button element
 */
export function NudgeButton({ userId }: { userId: string }) {
  const [nudgedAt, setNudgedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);
  const push = useToasts((s) => s.push);

  useEffect(() => {
    setNudgedAt(readStored(userId));
  }, [userId]);

  useEffect(() => {
    if (nudgedAt === null) return;
    const t = setInterval(() => {
      setNow(Date.now());
      if (Date.now() - nudgedAt >= COOLDOWN_MS) setNudgedAt(null);
    }, 60_000);
    return () => clearInterval(t);
  }, [nudgedAt]);

  const markNudged = useCallback(() => {
    const ts = Date.now();
    try {
      localStorage.setItem(key(userId), String(ts));
    } catch {
      /* storage unavailable */
    }
    setNow(ts);
    setNudgedAt(ts);
  }, [userId]);

  const onClick = async () => {
    setBusy(true);
    try {
      await sendNudge(userId, undefined);
      push({ variant: "success", message: "Nudge sent!" });
      markNudged();
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        push({
          variant: "warning",
          message: "You've already nudged this person in the last 24 hours",
        });
        markNudged();
      } else {
        push({
          variant: "danger",
          message: err instanceof Error ? err.message : "Could not send nudge",
        });
      }
    } finally {
      setBusy(false);
    }
  };

  const cooling = nudgedAt !== null;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={cooling || busy}
      className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-surface-strong outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
    >
      <Hand aria-hidden="true" className="size-4" />
      {cooling ? formatCooldown(now - nudgedAt) : "Nudge"}
    </button>
  );
}
