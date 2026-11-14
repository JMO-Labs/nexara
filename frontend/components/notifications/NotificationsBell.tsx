"use client";
/**
 * @file components/notifications/NotificationsBell.tsx
 * @brief Top-bar bell. Unread badge + anchored popover (no backdrop
 *        blur) of active notifications via NotifRow. SSE drives updates.
 */
import { useState, useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import { Bell, BellOff, AlertCircle } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";
import { Button } from "@/components/ui/Button";
import { NotifRow } from "./NotifRow";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  getUnreadCount,
  listActive,
  STREAM_PATH,
} from "@/lib/api/notifications";
import { useNotificationRegistry } from "@/lib/notifications/registry";
import type { NotificationItem } from "@/lib/notifications/types";
import { useSSE } from "@/hooks/useSSE";
import { useSyncHandler } from "@/hooks/useNotificationsSync";
import { useSession } from "@/stores/session";

const COUNT_KEY = ["notif", "count"] as const;
const ACTIVE_KEY = ["notif", "active"] as const;

/**
 * @brief Top-bar bell: unread badge + popover of active notifications.
 * @return bell element
 */
export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const reduced = useReducedMotion();
  const [pulse, setPulse] = useState(false);
  const [badgeKey, setBadgeKey] = useState(0);
  const prevCountRef = useRef(0);
  const debounceTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  const isAuthed = useSession((s) => s.status === "authenticated");
  const qc = useQueryClient();
  const { byKey } = useNotificationRegistry();
  const syncHandler = useSyncHandler();

  const { data: count } = useQuery({
    queryKey: COUNT_KEY,
    queryFn: getUnreadCount,
    enabled: isAuthed,
    staleTime: 30_000,
  });

  const {
    data: list,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ACTIVE_KEY,
    queryFn: listActive,
    enabled: isAuthed && open,
    staleTime: 30_000,
  });

  /** Optimistically drop the row (row component already called the API). */
  const optimisticDismiss = (id: string) => {
    qc.setQueryData<{ items: NotificationItem[] }>(ACTIVE_KEY, (prev) =>
      prev ? { ...prev, items: prev.items.filter((n) => n.id !== id) } : prev,
    );
    qc.invalidateQueries({ queryKey: COUNT_KEY });
  };

  useSSE(STREAM_PATH, {
    enabled: isAuthed,
    eventTypes: [
      "notification",
      "user_notification",
      "user_notification_dismissed",
      "user_preferences_updated",
    ],
    onMessage: (data, type) => {
      qc.invalidateQueries({ queryKey: ACTIVE_KEY });
      qc.invalidateQueries({ queryKey: COUNT_KEY });
      syncHandler(data, type);
    },
  });

  const unread = count?.count ?? 0;
  const items = list?.items ?? [];

  useEffect(() => {
    if (unread > prevCountRef.current && unread > 0) {
      if (debounceTimeoutRef.current) clearTimeout(debounceTimeoutRef.current);
      setPulse(true);
      setBadgeKey((k) => k + 1);
      debounceTimeoutRef.current = setTimeout(() => setPulse(false), 1000);
    }
    prevCountRef.current = unread;
    return () => {
      if (debounceTimeoutRef.current) clearTimeout(debounceTimeoutRef.current);
    };
  }, [unread]);

  // Outside-click + Esc to close (no Modal, no backdrop blur).
  useEffect(() => {
    if (!open) return;
    panelRef.current?.focus();
    const onClick = (e: MouseEvent) => {
      if (!wrapperRef.current) return;
      if (!wrapperRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        wrapperRef.current?.querySelector("button")?.focus();
      }
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={wrapperRef} className="relative">
      <motion.div
        animate={pulse && !reduced ? { rotate: [0, 8, -8, 0] } : { rotate: 0 }}
        transition={{ duration: 0.35, ease: "easeInOut" }}
      >
        <IconButton
          variant="ghost"
          aria-label={
            unread > 0 ? `Notifications, ${unread} unread` : "Notifications"
          }
          aria-expanded={open}
          aria-haspopup="dialog"
          tooltip="Notifications"
          tooltipSide="bottom"
          onClick={() => setOpen((v) => !v)}
          data-tour="bell"
        >
          <Bell aria-hidden width={20} height={20} />
        </IconButton>
      </motion.div>
      {unread > 0 && (
        <motion.span
          key={`badge-${badgeKey}`}
          data-testid="unread-badge"
          {...(reduced
            ? {}
            : {
                initial: { scale: 0.6, opacity: 0 },
                animate: { scale: 1, opacity: 1 },
                transition: { duration: 0.2, ease: "easeOut" as const },
              })}
          aria-hidden
          className="bg-destructive pointer-events-none absolute -top-1 -right-1 min-w-5 rounded-full px-1 text-center text-xs leading-5 font-semibold text-destructive-foreground"
        >
          {unread > 99 ? "99+" : unread}
        </motion.span>
      )}

      {open && (
        <div
          ref={panelRef}
          tabIndex={-1}
          role="dialog"
          aria-label="Notifications"
          className="bg-surface text-ink border-ink/10 z-[1100] fixed inset-x-0 top-14 mx-2 flex max-h-[min(70dvh,560px)] flex-col overflow-hidden rounded-2xl border shadow-lg outline-none sm:absolute sm:inset-x-auto sm:top-[calc(100%+8px)] sm:right-0 sm:mx-0 sm:w-96"
        >
          <div className="border-ink/10 flex items-center justify-between border-b p-4">
            <h2 className="font-display text-base font-semibold">
              Notifications
            </h2>
          </div>
          <div className="flex-1 overflow-auto">
            {isLoading && (
              <div className="flex flex-col gap-2 p-4">
                <Skeleton height={56} rounded="md" />
                <Skeleton height={56} rounded="md" />
                <Skeleton height={56} rounded="md" />
              </div>
            )}
            {!isLoading && error && (
              <div
                role="alert"
                className="flex flex-col items-center gap-3 p-6 text-center"
              >
                <AlertCircle
                  aria-hidden
                  width={24}
                  height={24}
                  className="text-destructive"
                />
                <p className="text-ink text-sm">Failed to load notifications</p>
                <Button size="sm" variant="ghost" onClick={() => refetch()}>
                  Retry
                </Button>
              </div>
            )}
            {!isLoading && !error && items.length === 0 && (
              <div className="flex flex-col items-center gap-2 p-6 text-center">
                <BellOff
                  aria-hidden
                  data-testid="notifications-empty-icon"
                  width={24}
                  height={24}
                  className="text-muted"
                />
                <p className="text-muted text-sm">All caught up.</p>
              </div>
            )}
            {items.map((n) => {
              const type = byKey.get(n.type);
              return type ? (
                <NotifRow
                  key={n.id}
                  item={n}
                  type={type}
                  onDismissed={optimisticDismiss}
                />
              ) : null;
            })}
          </div>
          {items.length > 0 && (
            <div className="border-ink/10 border-t p-2">
              <Button
                size="sm"
                variant="ghost"
                className="w-full"
                onClick={() => {
                  setOpen(false);
                  window.dispatchEvent(
                    new CustomEvent("notifications:drawer-open"),
                  );
                }}
              >
                View all
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
