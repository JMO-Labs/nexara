"use client";
/**
 * @file components/engagement/NudgeButton.tsx
 * @brief Button to nudge a member; 24h cooldown showing elapsed and
 *        remaining time ("Nudged 4h ago" / "Nudge again in 20h").
 *        On a 429 the real nudge time is unknown, so "Try again in ~24h".
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

/**
 * @brief Human label for time left until the user may nudge again.
 * @param remainingMs milliseconds until cooldown ends
 * @return e.g. "Nudge again in 20h" or "Nudge again in 35m"
 */
export function formatRemaining(remainingMs: number): string {
  const mins = Math.max(1, Math.ceil(remainingMs / 60_000));
  if (mins < 60) return `Nudge again in ${mins}m`;
  return `Nudge again in ${Math.ceil(mins / 60)}h`;
}

/** Cooldown record: timestamp plus whether it came from a 429. */
interface Cooldown {
  at: number;
  rateLimited: boolean;
}

const RL_PREFIX = "rl:";

function readStored(id: string): Cooldown | null {
  try {
    const raw = localStorage.getItem(key(id)) ?? "";
    const rateLimited = raw.startsWith(RL_PREFIX);
    const at = Number(rateLimited ? raw.slice(RL_PREFIX.length) : raw);
    return at && Date.now() - at < COOLDOWN_MS ? { at, rateLimited } : null;
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
  const [cooldown, setCooldown] = useState<Cooldown | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);
  const push = useToasts((s) => s.push);

  useEffect(() => {
    setCooldown(readStored(userId));
  }, [userId]);

  useEffect(() => {
    if (cooldown === null) return;
    const t = setInterval(() => {
      setNow(Date.now());
      if (Date.now() - cooldown.at >= COOLDOWN_MS) setCooldown(null);
    }, 60_000);
    return () => clearInterval(t);
  }, [cooldown]);

  const markNudged = useCallback(
    (rateLimited: boolean) => {
      const at = Date.now();
      try {
        localStorage.setItem(
          key(userId),
          `${rateLimited ? RL_PREFIX : ""}${at}`,
        );
      } catch {
        /* storage unavailable */
      }
      setNow(at);
      setCooldown({ at, rateLimited });
    },
    [userId],
  );

  const onClick = async () => {
    setBusy(true);
    try {
      await sendNudge(userId, undefined);
      push({ variant: "success", message: "Nudge sent!" });
      markNudged(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        push({
          variant: "warning",
          message: "You've already nudged this person in the last 24 hours",
        });
        markNudged(true);
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

  const cooling = cooldown !== null;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={cooling || busy}
      className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-surface-strong outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
    >
      <Hand aria-hidden="true" className="size-4" />
      {cooldown === null ? (
        "Nudge"
      ) : cooldown.rateLimited ? (
        "Try again in ~24h"
      ) : (
        <span className="flex flex-col items-start leading-tight">
          <span>{formatCooldown(now - cooldown.at)}</span>
          <span className="text-xs font-normal">
            {formatRemaining(COOLDOWN_MS - (now - cooldown.at))}
          </span>
        </span>
      )}
    </button>
  );
}
