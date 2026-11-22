"use client";
/**
 * @file components/inbox/InboxPage.tsx
 * @brief Outlook-style Inbox: folder rail | message list | reading pane in
 *        one glass frame. ?view= picks the folder, ?item= the open entry.
 *        Below lg the pane replaces the list; on phone folders are pills.
 */
import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Bookmark,
  List,
  Mail,
  Plus,
  type LucideIcon,
} from "lucide-react";
import { Button, EmptyState, Skeleton } from "@/components/ui";
import { PageHeader, Segmented } from "@/components/ui/page";
import { useNotificationsSync } from "@/hooks/useNotificationsSync";
import { markAllRead, markRead } from "@/lib/api/notifications";
import { cn } from "@/lib/utils";
import { InboxRow } from "./InboxRow";
import { ReadingPane } from "./ReadingPane";
import { useInboxItems, type Folder, type InboxEntry } from "./useInboxItems";

const FOLDERS: { value: Folder; label: string; Icon: LucideIcon }[] = [
  { value: "notifications", label: "Notifications", Icon: Bell },
  { value: "unread", label: "Unread", Icon: Mail },
  { value: "saved", label: "Saved", Icon: Bookmark },
  { value: "lists", label: "Lists", Icon: List },
];
const EMPTY: Record<Folder, { title: string; description: string }> = {
  notifications: {
    title: "No notifications yet",
    description: "Replies, mentions and updates will show up here.",
  },
  unread: {
    title: "You're all caught up",
    description: "New notifications will appear here.",
  },
  saved: {
    title: "Nothing saved yet",
    description: "Bookmark a post to keep it here.",
  },
  lists: {
    title: "No lists yet",
    description: "Create a list to share groceries, potlucks and more.",
  },
};
const RULE = "border-[color-mix(in_srgb,var(--nx-ink)_8%,transparent)]";

/**
 * @brief Inbox page body.
 * @return page element
 */
export function InboxPage() {
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  useNotificationsSync();
  const raw = params.get("view") as Folder | null;
  const folder: Folder = FOLDERS.some((f) => f.value === raw)
    ? raw!
    : "notifications";
  const itemId = params.get("item");
  const { items, isLoading, unreadCount, saved } = useInboxItems(folder);
  // Keep the opened entry even after it leaves the folder (e.g. Unread
  // drops it once marked read).
  const [opened, setOpened] = useState<InboxEntry | null>(null);
  const selected =
    items.find((i) => i.id === itemId) ??
    (opened?.id === itemId ? opened : null);
  const markAll = useMutation({
    mutationFn: markAllRead,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const go = (view: Folder, item?: string) => {
    const next = new URLSearchParams();
    if (view !== "notifications") next.set("view", view);
    if (item) next.set("item", item);
    router.push(next.toString() ? `/app/inbox?${next}` : "/app/inbox");
  };
  const open = (id: string) => {
    const e = items.find((i) => i.id === id);
    setOpened(e ?? null);
    if (e?.kind === "notif" && e.unread)
      void markRead(id).then(() =>
        qc.invalidateQueries({ queryKey: ["notifications"] }),
      );
    go(folder, id);
  };
  const current = FOLDERS.find((f) => f.value === folder)!;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Inbox"
        description="Notifications, saved posts and your lists."
      />
      <div className="md:hidden">
        <Segmented
          label="Inbox folders"
          value={folder}
          onChange={(v) => go(v)}
          options={FOLDERS.map((f) => ({ value: f.value, label: f.label }))}
        />
      </div>
      <div className="glass grid overflow-hidden rounded-[32px] md:h-[calc(100dvh-220px)] md:min-h-[520px] md:grid-cols-[200px_minmax(0,1fr)] lg:grid-cols-[210px_380px_minmax(0,1fr)]">
        <nav
          aria-label="Inbox folders"
          className={cn("hidden flex-col gap-1 border-r p-3 md:flex", RULE)}
        >
          {FOLDERS.map(({ value, label, Icon }) => {
            const active = value === folder;
            const n =
              value === "notifications" || value === "unread" ? unreadCount : 0;
            return (
              <button
                key={value}
                type="button"
                onClick={() => go(value)}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-full px-3.5 py-2 text-sm outline-none transition-colors focus-visible:outline-2 focus-visible:outline-accent",
                  active
                    ? "bg-surface-strong text-bg"
                    : "text-ink hover:bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)]",
                )}
              >
                <Icon className="size-4" aria-hidden="true" />
                <span className="flex-1 text-left">{label}</span>
                {value === "unread" && n > 0 && (
                  <span
                    className={cn(
                      "text-xs tabular-nums",
                      active ? "opacity-80" : "text-muted",
                    )}
                  >
                    {n}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
        <section
          aria-label={current.label}
          className={cn(
            "flex min-h-0 flex-col lg:border-r",
            RULE,
            selected && "max-lg:hidden",
          )}
        >
          <div className="flex items-center justify-between gap-2 px-4 pb-2 pt-4">
            <h2 className="text-base font-semibold">{current.label}</h2>
            {(folder === "notifications" || folder === "unread") &&
              unreadCount > 0 && (
                <Button
                  size="sm"
                  variant="ghost"
                  loading={markAll.isPending}
                  onClick={() => markAll.mutate()}
                >
                  Mark all read
                </Button>
              )}
            {folder === "lists" && (
              <div className="flex gap-1">
                <Button asChild size="sm" variant="secondary">
                  <Link href="/app/wishlists">Wishlists</Link>
                </Button>
                <Button asChild size="sm">
                  <Link href="/app/lists/new">
                    <Plus className="size-4" aria-hidden="true" /> New list
                  </Link>
                </Button>
              </div>
            )}
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2 pb-3">
            {isLoading ? (
              [0, 1, 2, 3].map((i) => (
                <Skeleton
                  key={i}
                  height={52}
                  rounded="lg"
                  className="mx-1 my-1"
                />
              ))
            ) : items.length === 0 ? (
              <EmptyState
                compact
                icon={current.Icon}
                title={EMPTY[folder].title}
                description={EMPTY[folder].description}
                action={
                  folder === "lists" && (
                    <Button asChild size="sm">
                      <Link href="/app/lists/new">
                        <Plus className="size-4" aria-hidden="true" /> New list
                      </Link>
                    </Button>
                  )
                }
              />
            ) : (
              items.map((e) => (
                <InboxRow
                  key={e.id}
                  entry={e}
                  selected={e.id === itemId}
                  onSelect={() => open(e.id)}
                />
              ))
            )}
            {folder === "saved" && saved.hasNextPage && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-2 self-center"
                disabled={saved.isFetchingNextPage}
                onClick={() => void saved.fetchNextPage()}
              >
                Load more
              </Button>
            )}
          </div>
        </section>
        <section
          aria-label="Reading pane"
          className={cn(
            "min-h-0 md:col-start-2 lg:col-start-3",
            !selected && "max-lg:hidden",
          )}
        >
          <ReadingPane
            entry={selected}
            onBack={() => go(folder)}
            emptyText={
              folder === "lists" && items.length === 0
                ? "Create your first list to see it here."
                : undefined
            }
          />
        </section>
      </div>
    </div>
  );
}
