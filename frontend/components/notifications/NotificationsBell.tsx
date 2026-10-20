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
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Sheet from "@mui/joy/Sheet";
import Badge from "@mui/joy/Badge";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  BellIcon,
  CheckIcon,
  AtSymbolIcon,
  ChatBubbleLeftIcon,
  HeartIcon,
  CalendarIcon,
  SparklesIcon,
  DocumentTextIcon,
  PhotoIcon,
  InboxIcon,
} from "@heroicons/react/24/outline";
import type { ComponentType, SVGProps } from "react";
import { IconButton } from "@/components/ui/IconButton";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  getUnreadCount,
  listNotifications,
  markAllRead,
  markRead,
  STREAM_PATH,
  type NotificationItem,
  type NotificationListResponse,
} from "@/lib/api/notifications";
import { useSSE } from "@/hooks/useSSE";
import { useSession } from "@/stores/session";

const COUNT_KEY = ["notifications", "unread-count"] as const;
const LIST_KEY = ["notifications", "list"] as const;

type IconCmp = ComponentType<SVGProps<SVGSVGElement>>;

const TYPE_META: Record<string, { label: string; icon: IconCmp }> = {
  mention: { label: "Mention", icon: AtSymbolIcon },
  comment: { label: "Comment", icon: ChatBubbleLeftIcon },
  reaction: { label: "Reaction", icon: HeartIcon },
  event_rsvp: { label: "Event RSVP", icon: CalendarIcon },
  prompt: { label: "Prompt", icon: SparklesIcon },
  prompt_summary: { label: "Prompt summary", icon: SparklesIcon },
  gallery_activity: { label: "Gallery", icon: PhotoIcon },
  post: { label: "Post", icon: DocumentTextIcon },
};

function metaFor(type: string): { label: string; icon: IconCmp } {
  return TYPE_META[type] ?? { label: type.replace(/_/g, " "), icon: InboxIcon };
}

export function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [pulse, setPulse] = useState(false);
  const [badgeKey, setBadgeKey] = useState(0);
  const prevCountRef = useRef(0);
  const debounceTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const wrapperRef = useRef<HTMLDivElement | null>(null);

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
    const onClick = (e: MouseEvent) => {
      if (!wrapperRef.current) return;
      if (!wrapperRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <Box ref={wrapperRef} sx={{ position: "relative" }}>
      <Badge
        key={`badge-${badgeKey}`}
        badgeContent={unread > 99 ? "99+" : unread}
        color="danger"
        invisible={unread === 0}
        size="sm"
      >
        <motion.div
          animate={pulse ? { rotate: [0, 8, -8, 0] } : { rotate: 0 }}
          transition={{ duration: 0.35, ease: "easeInOut" }}
        >
          <IconButton
            tooltip="Notifications"
            variant="plain"
            color="neutral"
            aria-label={
              unread > 0 ? `Notifications, ${unread} unread` : "Notifications"
            }
            aria-expanded={open}
            aria-haspopup="dialog"
            onClick={() => setOpen((v) => !v)}
            data-tour="bell"
          >
            <BellIcon aria-hidden width={20} height={20} />
          </IconButton>
        </motion.div>
      </Badge>

      {open && (
        <Sheet
          role="dialog"
          aria-label="Notifications"
          variant="outlined"
          sx={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            width: { xs: 320, sm: 380 },
            maxHeight: "min(70dvh, 560px)",
            borderRadius: "lg",
            boxShadow: "lg",
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
            zIndex: 1100,
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}
          >
            <Typography
              level="title-md"
              sx={{ fontFamily: "var(--font-display)" }}
            >
              Notifications
            </Typography>
            {unread > 0 && (
              <Button
                size="sm"
                variant="plain"
                onClick={() => markAll.mutate()}
                loading={markAll.isPending}
              >
                Mark all read
              </Button>
            )}
          </Stack>
          <Box sx={{ overflow: "auto", flex: 1 }}>
            {isLoading && (
              <Stack spacing={1} sx={{ p: 2 }}>
                <Skeleton height={56} rounded="md" />
                <Skeleton height={56} rounded="md" />
                <Skeleton height={56} rounded="md" />
              </Stack>
            )}
            {!isLoading && error && (
              <Typography
                level="body-sm"
                color="danger"
                sx={{ p: 4, textAlign: "center" }}
              >
                Could not load notifications.
                {unread > 0 && ` (${unread} unread reported)`}
              </Typography>
            )}
            {!isLoading && !error && (list?.items.length ?? 0) === 0 && (
              <Typography
                level="body-sm"
                color="neutral"
                sx={{ p: 4, textAlign: "center" }}
              >
                {unread > 0
                  ? `${unread} unread reported but list is empty — try refresh.`
                  : "You’re all caught up."}
              </Typography>
            )}
            {!isLoading &&
              list?.items.map((n) => (
                <Row
                  key={n.id}
                  item={n}
                  onAck={(id) => ackOne.mutate(id)}
                  onDismiss={dismissOne}
                  ackPending={ackOne.isPending && ackOne.variables === n.id}
                  onNavigate={() => setOpen(false)}
                />
              ))}
          </Box>
        </Sheet>
      )}
    </Box>
  );
}

interface RowProps {
  item: NotificationItem;
  onAck: (id: string) => void;
  onDismiss: (id: string) => void;
  onNavigate: () => void;
  ackPending: boolean;
}

function Row({ item, onAck, onDismiss, onNavigate, ackPending }: RowProps) {
  const unread = !item.read_at;
  const { label, icon: Icon } = metaFor(item.type);
  const message =
    typeof item.payload?.message === "string" ? item.payload.message : label;
  const link =
    typeof item.payload?.link === "string" ? item.payload.link : null;

  const Body = (
    <Stack
      direction="row"
      spacing={1.5}
      alignItems="flex-start"
      sx={{
        px: 2,
        py: 1.5,
        borderBottom: "1px solid",
        borderColor: "divider",
        background: unread ? "primary.softBg" : "transparent",
        "&:hover": { background: "neutral.softBg" },
      }}
    >
      <Box
        aria-label={label}
        title={label}
        sx={{
          flexShrink: 0,
          width: 32,
          height: 32,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: unread ? "primary.plainColor" : "neutral.plainColor",
          background: unread ? "primary.softBg" : "neutral.softBg",
        }}
      >
        <Icon aria-hidden width={18} height={18} />
      </Box>
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography level="body-xs" color="neutral" sx={{ mb: 0.25 }}>
          {formatTime(item.created_at)}
        </Typography>
        <Typography level="body-sm" sx={{ wordBreak: "break-word" }}>
          {message}
        </Typography>
      </Box>
      {unread && (
        <IconButton
          tooltip="Acknowledge"
          aria-label="Acknowledge notification"
          size="sm"
          variant="plain"
          color="neutral"
          loading={ackPending}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onAck(item.id);
          }}
        >
          <CheckIcon aria-hidden width={16} height={16} />
        </IconButton>
      )}
    </Stack>
  );

  if (!link) return Body;
  return (
    <Box
      component={Link}
      href={link}
      sx={{ display: "block", color: "inherit", textDecoration: "none" }}
      onClick={() => {
        onDismiss(item.id);
        onNavigate();
      }}
    >
      {Body}
    </Box>
  );
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86_400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}
