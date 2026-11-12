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
import { formatTime } from "./formatTime";
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
    const listId = typeof ctx.listId === "string" ? ctx.listId : "";
    return (
      <ListNotification
        notification={{
          id: item.id,
          type: item.type,
          context: ctx,
          createdAt: item.created_at,
        }}
        href={listId ? `/app/lists/${encodeURIComponent(listId)}` : undefined}
        unread={!item.read_at}
        ackPending={ackPending}
        onAck={onAck}
        onDismiss={onDismiss}
        onNavigate={() => {
          onDismiss(item.id);
          onNavigate();
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
      data-row
      tabIndex={link ? undefined : 0}
      onKeyDown={
        link
          ? undefined
          : (e) => {
              if (e.target === e.currentTarget && e.key === "Enter" && unread)
                onAck(item.id);
            }
      }
      className={cn(
        "border-ink/10 hover:bg-surface focus-visible:ring-accent flex items-start gap-3 border-b px-4 py-3 focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-inset",
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
        <p className="text-muted mb-2 text-xs">{formatTime(item.created_at)}</p>
        <p className="text-sm break-words">{message}</p>
      </div>
      {unread && (
        <span
          role="img"
          aria-label="Unread"
          className="bg-accent mt-2 size-2 shrink-0 rounded-full"
        />
      )}
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
      className="focus-visible:ring-accent block text-inherit no-underline focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-inset"
      onClick={() => {
        onDismiss(item.id);
        onNavigate();
      }}
    >
      {body}
    </Link>
  );
}
