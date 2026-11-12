"use client";
/**
 * @file components/notifications/NotificationRow.tsx
 * @brief Single notification row: type icon, time, message, acknowledge.
 */
import { safeInternalLink } from "@/lib/safeLink";
import type { ComponentType, SVGProps } from "react";
import Link from "next/link";
import {
  Check,
  AtSign,
  MessageSquare,
  Heart,
  Calendar,
  Sparkles,
  FileText,
  Image as ImageIcon,
  Inbox,
} from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";
import { cn } from "@/lib/utils";
import {
  ListNotification,
  isListNotificationType,
} from "./ListNotificationRenderer";
import type { NotificationItem } from "@/lib/api/notifications";

type IconCmp = ComponentType<SVGProps<SVGSVGElement>>;

const TYPE_META: Record<string, { label: string; icon: IconCmp }> = {
  mention: { label: "Mention", icon: AtSign },
  comment: { label: "Comment", icon: MessageSquare },
  reaction: { label: "Reaction", icon: Heart },
  event_rsvp: { label: "Event RSVP", icon: Calendar },
  prompt: { label: "Prompt", icon: Sparkles },
  prompt_summary: { label: "Prompt summary", icon: Sparkles },
  gallery_activity: { label: "Gallery", icon: ImageIcon },
  post: { label: "Post", icon: FileText },
};

function metaFor(type: string): { label: string; icon: IconCmp } {
  return TYPE_META[type] ?? { label: type.replace(/_/g, " "), icon: Inbox };
}

/** @brief Relative time string. */
export function formatTime(iso: string): string {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86_400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}

export interface NotificationRowProps {
  item: NotificationItem;
  onAck: (id: string) => void;
  onDismiss: (id: string) => void;
  onNavigate: () => void;
  ackPending: boolean;
}

/**
 * @brief Notification row; links when payload.link is set.
 * @param props see NotificationRowProps
 * @return row element
 */
export function NotificationRow({
  item,
  onAck,
  onDismiss,
  onNavigate,
  ackPending,
}: NotificationRowProps) {
  if (isListNotificationType(item.type)) {
    const ctx = (item.payload ?? {}) as Record<string, unknown>;
    return (
      <ListNotification
        notification={{
          id: item.id,
          type: item.type,
          context: ctx,
          createdAt: item.created_at,
        }}
        onDismiss={onDismiss}
        onNavigate={(listId) => {
          onDismiss(item.id);
          onNavigate();
          if (listId)
            window.location.assign(`/app/lists/${encodeURIComponent(listId)}`);
        }}
      />
    );
  }
  const unread = !item.read_at;
  const { label, icon: Icon } = metaFor(item.type);
  const message =
    typeof item.payload?.message === "string" ? item.payload.message : label;
  const link = safeInternalLink(item.payload?.link);

  const body = (
    <div
      className={cn(
        "border-ink/10 hover:bg-surface flex items-start gap-3 border-b px-4 py-3",
        unread && "bg-surface",
      )}
    >
      <span
        aria-label={label}
        title={label}
        className={cn(
          "flex size-8 shrink-0 items-center justify-center rounded-full",
          unread ? "bg-accent text-surface-strong" : "bg-surface text-muted",
        )}
      >
        <Icon aria-hidden width={18} height={18} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-muted mb-0.5 text-xs">
          {formatTime(item.created_at)}
        </p>
        <p className="text-sm break-words">{message}</p>
      </div>
      {unread && (
        <IconButton
          aria-label="Acknowledge notification"
          size="sm"
          variant="ghost"
          disabled={ackPending}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onAck(item.id);
          }}
        >
          <Check aria-hidden width={16} height={16} />
        </IconButton>
      )}
    </div>
  );

  if (!link) return body;
  return (
    <Link
      href={link}
      className="text-inherit no-underline"
      onClick={() => {
        onDismiss(item.id);
        onNavigate();
      }}
    >
      {body}
    </Link>
  );
}
