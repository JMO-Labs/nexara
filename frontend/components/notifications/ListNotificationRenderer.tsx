"use client";
/**
 * @file components/notifications/ListNotificationRenderer.tsx
 * @brief Renderers for the five list notification types (list.item,
 *        list.signup, list.completed, list.expiring, list.member).
 */
import type { ComponentType, SVGProps } from "react";
import { List, CircleCheck, Check, Clock, User, X } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { IconButton } from "@/components/ui/IconButton";
import { formatTime } from "./formatTime";

type IconCmp = ComponentType<SVGProps<SVGSVGElement>>;

export interface ListNotificationData {
  id: string;
  type: string;
  context: Record<string, unknown>;
  createdAt: string;
}

export interface ListNotificationProps {
  notification: ListNotificationData;
  onDismiss: (id: string) => void;
  onNavigate: (listId: string) => void;
  /** Target URL; when absent the row is not a link. */
  href?: string;
  unread?: boolean;
  ackPending?: boolean;
  onAck?: (id: string) => void;
}

const s = (v: unknown, d = ""): string => (typeof v === "string" ? v : d);

/** Title templates per type, interpolated from notification.context. */
export const LIST_TITLES: Record<
  string,
  (c: Record<string, unknown>) => string
> = {
  "list.item": (c) => `New item in ${s(c.listName, "your list")}`,
  "list.signup": (c) => `${s(c.userName, "Someone")} claimed`,
  "list.completed": () => "Item marked done",
  "list.expiring": () => "Expires in 1 day",
  "list.member": (c) => `Added by ${s(c.inviterName, "a member")}`,
};

const ICONS: Record<string, IconCmp> = {
  "list.item": List,
  "list.signup": CircleCheck,
  "list.completed": Check,
  "list.expiring": Clock,
  "list.member": User,
};

/**
 * @brief Whether a notification type is a list type.
 * @param type notification type
 * @return true for the five list types
 */
export function isListNotificationType(type: string): boolean {
  return type in LIST_TITLES;
}

/**
 * @brief One list notification row: icon, title, details, time, dismiss.
 * @param props see ListNotificationProps
 * @return row element
 */
export function ListNotification({
  notification,
  onDismiss,
  onNavigate,
  href,
  unread = false,
  ackPending = false,
  onAck,
}: ListNotificationProps) {
  const { id, type, context, createdAt } = notification;
  const Icon = ICONS[type] ?? List;
  const title = (LIST_TITLES[type] ?? (() => type))(context);
  const detail = s(context.itemTitle) || s(context.detail);
  const listId = s(context.listId);

  const content = (
    <>
      <Icon
        aria-hidden
        width={20}
        height={20}
        className="text-accent mt-0.5 shrink-0"
      />
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium break-words">{title}</span>
        {detail && (
          <span className="text-muted block text-xs break-words">{detail}</span>
        )}
      </span>
      <span className="text-muted shrink-0 text-xs">
        {formatTime(createdAt)}
      </span>
    </>
  );
  const cls = "flex min-w-0 flex-1 items-start gap-3 px-4 py-3 text-left";

  return (
    <div
      className={cn(
        "border-ink/10 hover:bg-surface flex items-center border-b",
        unread && "bg-surface",
      )}
    >
      {href ? (
        <Link
          href={href}
          className={cn(cls, "text-inherit no-underline")}
          onClick={() => onNavigate(listId)}
        >
          {content}
        </Link>
      ) : (
        <div className={cls}>{content}</div>
      )}
      {unread && onAck && (
        <IconButton
          aria-label="Acknowledge notification"
          size="sm"
          variant="ghost"
          disabled={ackPending}
          onClick={() => onAck(id)}
        >
          <Check aria-hidden width={16} height={16} />
        </IconButton>
      )}
      <button
        type="button"
        aria-label="Dismiss"
        onClick={() => onDismiss(id)}
        className="text-muted focus-visible:outline-accent mr-2 rounded p-1 hover:bg-gray-200 focus-visible:outline-2"
      >
        <X aria-hidden width={16} height={16} />
      </button>
    </div>
  );
}
