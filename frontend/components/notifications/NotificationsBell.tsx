"use client";
/**
 * @file components/notifications/NotificationsBell.tsx
 * @brief Top-bar bell. Shows unread badge, opens an anchored popover
 *        (no backdrop blur) listing recent notifications. Each row shows
 *        type, summary, timestamp and an Acknowledge button. SSE drives
 *        live count + list updates.
 */
import { useState, useEffect, useRef } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import { Bell } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";
import { Button } from "@/components/ui/Button";
import { NotificationRow } from "./NotificationRow";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  getUnreadCount,
  listNotifications,
  markAllRead,
  markRead,
  STREAM_PATH,
  type NotificationListResponse,
} from "@/lib/api/notifications";
import { useSSE } from "@/hooks/useSSE";
import { useSession } from "@/stores/session";

const COUNT_KEY = ["notifications", "unread-count"] as const;
const LIST_KEY = ["notifications", "list"] as const;

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
  } = useQuery({
    queryKey: LIST_KEY,
    queryFn: () => listNotifications(),
    enabled: isAuthed,
    staleTime: 30_000,
  });

  const markAll = useMutation({
    mutationFn: markAllRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: COUNT_KEY });
      qc.invalidateQueries({ queryKey: LIST_KEY });
    },
  });

  const ackOne = useMutation({
    mutationFn: (id: string) => markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: COUNT_KEY });
      qc.invalidateQueries({ queryKey: LIST_KEY });
    },
  });

  const dismissOne = (id: string) => {
    qc.setQueryData<NotificationListResponse>(LIST_KEY, (prev) =>
      prev ? { ...prev, items: prev.items.filter((n) => n.id !== id) } : prev,
    );
    ackOne.mutate(id);
  };

  useSSE(STREAM_PATH, {
    enabled: isAuthed,
    eventTypes: ["notification", "user_notification"],
    onMessage: () => {
      qc.invalidateQueries({ queryKey: COUNT_KEY });
      if (open) qc.invalidateQueries({ queryKey: LIST_KEY });
    },
  });

  const unread = count?.count ?? 0;

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
          className="bg-surface text-ink border-ink/10 absolute top-[calc(100%+8px)] right-0 z-[1100] flex outline-none max-h-[min(70dvh,560px)] w-80 flex-col overflow-hidden rounded-2xl border shadow-lg sm:w-96"
        >
          <div className="border-ink/10 flex items-center justify-between border-b p-4">
            <h2 className="font-display text-base font-semibold">
              Notifications
            </h2>
            {unread > 0 && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => markAll.mutate()}
                loading={markAll.isPending}
              >
                Mark all read
              </Button>
            )}
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
              <p className="text-destructive p-6 text-center text-sm">
                Could not load notifications.
                {unread > 0 && ` (${unread} unread reported)`}
              </p>
            )}
            {!isLoading && !error && (list?.items.length ?? 0) === 0 && (
              <p className="text-muted p-6 text-center text-sm">
                {unread > 0
                  ? `${unread} unread reported but list is empty — try refresh.`
                  : "You’re all caught up."}
              </p>
            )}
            {!isLoading &&
              list?.items.map((n) => (
                <NotificationRow
                  key={n.id}
                  item={n}
                  onAck={(id) => ackOne.mutate(id)}
                  onDismiss={dismissOne}
                  ackPending={ackOne.isPending && ackOne.variables === n.id}
                  onNavigate={() => setOpen(false)}
                />
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
