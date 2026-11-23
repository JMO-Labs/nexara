"use client";
/**
 * @file components/notifications/NotificationsBell.tsx
 * @brief Top-bar bell (glass circle, red dot when unread) + anchored glass
 *        popover of active notifications as Inbox rows; a row opens it in
 *        the Inbox. SSE drives updates.
 */
import { useState, useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import { Bell, BellOff, AlertCircle } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { InboxRow } from "@/components/inbox/InboxRow";
import { notifEntry } from "@/components/inbox/useInboxItems";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  getUnreadCount,
  listActive,
  markAllRead,
  markRead,
  STREAM_PATH,
} from "@/lib/api/notifications";
import { useNotificationRegistry } from "@/lib/notifications/registry";
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
  const router = useRouter();
  const t = useTranslations();
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

  const openItem = (id: string, unreadRow: boolean) => {
    setOpen(false);
    if (unreadRow)
      void markRead(id).then(() => {
        qc.invalidateQueries({ queryKey: COUNT_KEY });
        qc.invalidateQueries({ queryKey: ACTIVE_KEY });
        qc.invalidateQueries({ queryKey: ["notifications"] });
      });
    router.push(`/app/inbox?item=${encodeURIComponent(id)}`);
  };
  const markAll = async () => {
    await markAllRead();
    qc.invalidateQueries({ queryKey: COUNT_KEY });
    qc.invalidateQueries({ queryKey: ACTIVE_KEY });
    qc.invalidateQueries({ queryKey: ["notifications"] });
  };

  return (
    <div ref={wrapperRef} className="relative">
      <motion.div
        animate={pulse && !reduced ? { rotate: [0, 8, -8, 0] } : { rotate: 0 }}
        transition={{ duration: 0.35, ease: "easeInOut" }}
      >
        <IconButton
          variant="ghost"
          className="glass-btn size-10 md:size-11"
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
                initial: { scale: 0.4, opacity: 0 },
                animate: { scale: 1, opacity: 1 },
                transition: { duration: 0.2, ease: "easeOut" as const },
              })}
          aria-hidden
          className="pointer-events-none absolute top-2.5 right-2.5 size-[7px] rounded-full bg-[var(--nx-red)] md:top-[11px] md:right-3"
        />
      )}

      {open && (
        <div
          ref={panelRef}
          tabIndex={-1}
          role="dialog"
          aria-label="Notifications"
          className="glass text-ink z-[1100] fixed bg-[var(--nx-glass-solid)] shadow-[0_24px_60px_-24px_rgba(0,0,0,0.55)] inset-x-0 top-14 mx-3 flex max-h-[min(70dvh,560px)] flex-col overflow-hidden rounded-[28px] outline-none sm:absolute sm:inset-x-auto sm:top-[calc(100%+10px)] sm:right-0 sm:mx-0 sm:w-[380px]"
        >
          <div className="flex items-center justify-between gap-2 px-5 pt-4 pb-2">
            <h2 className="text-base font-semibold">Notifications</h2>
            {unread > 0 && (
              <Button size="sm" variant="ghost" onClick={() => void markAll()}>
                Mark all read
              </Button>
            )}
          </div>
          <div className="flex flex-1 flex-col gap-0.5 overflow-auto px-2 pb-2">
            {isLoading && (
              <div className="flex flex-col gap-2 p-2">
                <Skeleton height={52} rounded="lg" />
                <Skeleton height={52} rounded="lg" />
                <Skeleton height={52} rounded="lg" />
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
              <div className="flex flex-col items-center gap-3 p-8 text-center">
                <span className="glass-item grid size-12 place-items-center rounded-full">
                  <BellOff
                    aria-hidden
                    data-testid="notifications-empty-icon"
                    width={20}
                    height={20}
                    className="text-muted"
                  />
                </span>
                <p className="text-muted text-sm">You&apos;re all caught up.</p>
              </div>
            )}
            {items.slice(0, 8).map((n) => {
              const type = byKey.get(n.type);
              if (!type) return null;
              const e = notifEntry(n, type, (k) => t(k));
              return (
                <InboxRow
                  key={n.id}
                  entry={e}
                  selected={false}
                  onSelect={() => openItem(n.id, e.unread)}
                />
              );
            })}
          </div>
          <div className="border-t border-[color-mix(in_srgb,var(--nx-ink)_8%,transparent)] p-2">
            <Button asChild size="sm" variant="ghost" className="w-full">
              <Link href="/app/inbox" onClick={() => setOpen(false)}>
                Open inbox
              </Link>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
