"use client";
/**
 * @file components/inbox/useInboxItems.ts
 * @brief Normalises notifications, saved posts and lists into one row shape
 *        for the Outlook-style Inbox list column.
 */
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  Bell,
  CalendarDays,
  Image as ImageIcon,
  MessageCircleQuestion,
  Puzzle,
  Settings2,
  Users,
  type LucideIcon,
} from "lucide-react";
import { listNotifications } from "@/lib/api/notifications";
import { listBookmarks } from "@/lib/api/bookmarks";
import { useLists } from "@/hooks/useLists";
import { useCommunityId } from "@/hooks/useCommunityId";
import { useNotificationRegistry } from "@/lib/notifications/registry";
import { renderNotif } from "@/lib/notifications/renderers";
import type {
  Category,
  NotificationItem,
  NotificationTypeDescriptor,
} from "@/lib/notifications/types";
import type { Post } from "@/lib/api/posts";
import type { List } from "@/lib/api/listTypes";

export type Folder = "notifications" | "unread" | "saved" | "lists";

export type InboxEntry = {
  id: string;
  title: string;
  snippet: string;
  time: string;
  unread: boolean;
  Icon?: LucideIcon;
  avatar?: { name: string; src: string | null };
  color?: string | null;
} & (
  | {
      kind: "notif";
      notif: NotificationItem;
      type: NotificationTypeDescriptor;
      link: string | null;
    }
  | { kind: "saved"; post: Post }
  | { kind: "list"; list: List }
);

const CATEGORY_ICON: Record<Category, LucideIcon> = {
  social: Users,
  event: CalendarDays,
  gallery: ImageIcon,
  prompt: MessageCircleQuestion,
  system: Settings2,
  plugin: Puzzle,
};

/**
 * @brief Notification -> inbox entry (shared with the bell popover).
 * @param n notification
 * @param type registry descriptor
 * @param t translator
 * @return entry
 */
export function notifEntry(
  n: NotificationItem,
  type: NotificationTypeDescriptor,
  t: (k: string) => string,
): InboxEntry {
  const r = renderNotif(type, n.payload ?? {}, t);
  return {
    kind: "notif",
    id: n.id,
    title: r.title,
    snippet: r.body,
    time: n.created_at,
    unread: !n.read_at && !n.dismissed_at,
    Icon: CATEGORY_ICON[type.category] ?? Bell,
    notif: n,
    type,
    link: r.link,
  };
}

/**
 * @brief Rows for a folder plus the unread notification count.
 * @param folder active folder
 * @return entries, loading flag, unread count
 */
export function useInboxItems(folder: Folder) {
  const t = useTranslations();
  const { byKey } = useNotificationRegistry();
  const communityId = useCommunityId();
  const notifs = useQuery({
    queryKey: ["notifications", "history"],
    queryFn: () => listNotifications(),
  });
  const saved = useInfiniteQuery({
    queryKey: ["bookmarks", "list"],
    queryFn: ({ pageParam }) => listBookmarks(pageParam, 20),
    initialPageParam: null as string | null,
    getNextPageParam: (last) =>
      last.pagination.has_more ? last.pagination.cursor : undefined,
    enabled: folder === "saved",
  });
  const lists = useLists(folder === "lists" ? communityId : undefined);

  const allNotifs = (notifs.data?.items ?? []) as unknown as NotificationItem[];
  const isUnread = (n: NotificationItem) => !n.read_at && !n.dismissed_at;
  const unreadCount = allNotifs.filter(isUnread).length;

  let items: InboxEntry[] = [];
  let isLoading = false;
  if (folder === "notifications" || folder === "unread") {
    isLoading = notifs.isLoading;
    items = allNotifs
      .filter((n) => folder === "notifications" || isUnread(n))
      .flatMap((n) => {
        const type = byKey.get(n.type);
        return type ? [notifEntry(n, type, (k) => t(k))] : [];
      });
  } else if (folder === "saved") {
    isLoading = saved.isLoading;
    items = (saved.data?.pages ?? [])
      .flatMap((p) => p.bookmarks)
      .map((b) => ({
        kind: "saved",
        id: b.id,
        title: b.post.author.display_name,
        snippet: b.post.content,
        time: b.bookmarked_at,
        unread: false,
        avatar: {
          name: b.post.author.display_name,
          src: b.post.author.avatar_url,
        },
        post: { ...b.post, is_bookmarked: true },
      }));
  } else {
    isLoading = lists.isLoading;
    const data: List[] = lists.data?.lists ?? [];
    items = data.map((l) => ({
      kind: "list",
      id: l.id,
      title: l.title,
      snippet: `${l.completedCount}/${l.itemCount} done${l.description ? ` · ${l.description}` : ""}`,
      time: l.updatedAt,
      unread: false,
      color: l.color,
      list: l,
    }));
  }
  return { items, isLoading, unreadCount, saved };
}
