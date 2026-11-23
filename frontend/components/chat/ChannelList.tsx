"use client";
/**
 * @file components/chat/ChannelList.tsx
 * @brief Sidebar list of channels + DM threads as glass ThreadRows. Supports
 *        text filter and All/Groups/Direct segment; shows unread per thread.
 */
import * as React from "react";
import { motion } from "framer-motion";
import { fadeInOut, useMotionProps } from "@/components/ui/motion";
import { Avatar, EmptyState, Skeleton } from "@/components/ui";
import { groupColor } from "@/lib/groupColor";
import type { ChatChannel, DmThread } from "@/lib/api/chat";
import type { HomeChatThread } from "@/lib/api/home";
import { agoShort } from "./format";
import { ThreadRow } from "./ThreadRow";

export type ChatSegment = "all" | "groups" | "direct";

export interface ChannelListProps {
  channels: ChatChannel[];
  dms: DmThread[];
  activeId: string | null;
  unread: Record<string, number>;
  onSelect: (channelId: string) => void;
  onDeleteDm?: (channelId: string) => void;
  loading?: boolean;
  /** Case-insensitive text filter on names/usernames. */
  query?: string;
  /** Which kinds of thread to show. */
  segment?: ChatSegment;
  /** Home-chats data by channel id: preview, unread and last activity. */
  threads?: Record<string, HomeChatThread>;
}

/** @brief "Richard: he bud" preview, or null with no message. */
function previewOf(t?: HomeChatThread): string | null {
  const m = t?.last_message;
  if (!m) return null;
  return m.author_name ? `${m.author_name}: ${m.content}` : m.content;
}

/** @brief Newest activity first; threads without activity last. */
function byActivity<T>(
  items: T[],
  id: (x: T) => string,
  threads?: Record<string, HomeChatThread>,
): T[] {
  const at = (x: T) => threads?.[id(x)]?.last_activity_at ?? "";
  return [...items].sort((a, b) => at(b).localeCompare(at(a)));
}

function Heading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="px-2 pb-1 pt-2 text-xs font-medium text-[var(--nx-muted)]">
      {children}
    </h2>
  );
}

/**
 * @brief Filtered thread list.
 * @param props see ChannelListProps
 * @return list element
 */
export function ChannelList({
  channels,
  dms,
  activeId,
  unread,
  onSelect,
  onDeleteDm,
  loading,
  query = "",
  segment = "all",
  threads,
}: ChannelListProps) {
  const fade = useMotionProps(fadeInOut);
  if (loading) {
    return (
      <motion.div
        data-testid="channel-skeleton"
        className="flex flex-col gap-2 p-2"
        {...fade}
      >
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} height={48} />
        ))}
      </motion.div>
    );
  }

  const q = query.trim().toLowerCase();
  const grouped =
    segment === "direct"
      ? []
      : channels
          .filter((c) => c.channel_type !== "direct")
          .filter((c) => !q || c.name.toLowerCase().includes(q));
  const direct =
    segment === "groups"
      ? []
      : dms.filter(
          (d) =>
            !q ||
            d.peer.display_name.toLowerCase().includes(q) ||
            d.peer.username.toLowerCase().includes(q),
        );

  if (grouped.length === 0 && direct.length === 0) {
    return (
      <EmptyState
        compact
        title={q ? "No matches" : "No conversations"}
        description={
          q ? "Try a different search." : "Start one with New message."
        }
      />
    );
  }

  const row = "glass-item";
  const unreadOf = (id: string) =>
    unread[id] ?? threads?.[id]?.unread_count ?? 0;
  const stampOf = (id: string) => {
    const t = threads?.[id];
    return t?.last_message ? agoShort(t.last_activity_at) : null;
  };
  return (
    <div className="flex flex-col gap-1">
      {grouped.length > 0 && (
        <section aria-label="Groups">
          <Heading>Groups</Heading>
          <ul className="flex list-none flex-col gap-1.5 p-0">
            {byActivity(grouped, (c) => c.id, threads).map((c) => (
              <li key={c.id}>
                <ThreadRow
                  dense
                  name={`# ${c.name}`}
                  preview={previewOf(threads?.[c.id]) ?? c.channel_type}
                  timeLabel={stampOf(c.id)}
                  color={groupColor(c.subgroup_id, null)}
                  unread={unreadOf(c.id)}
                  selected={activeId === c.id}
                  onClick={() => onSelect(c.id)}
                  className={row}
                />
              </li>
            ))}
          </ul>
        </section>
      )}
      {direct.length > 0 && (
        <section aria-label="People">
          <Heading>People</Heading>
          <ul className="flex list-none flex-col gap-1.5 p-0">
            {byActivity(direct, (d) => d.channel_id, threads).map((d) => (
              <li key={d.channel_id}>
                <ThreadRow
                  dense
                  name={d.peer.display_name}
                  preview={
                    previewOf(threads?.[d.channel_id]) ?? `@${d.peer.username}`
                  }
                  timeLabel={stampOf(d.channel_id)}
                  color="var(--nx-muted)"
                  avatar={
                    <Avatar
                      src={d.peer.avatar_url ?? undefined}
                      size="md"
                      name={d.peer.display_name}
                      userId={d.peer.id}
                    />
                  }
                  unread={unreadOf(d.channel_id)}
                  selected={activeId === d.channel_id}
                  onClick={() => onSelect(d.channel_id)}
                  onDelete={
                    onDeleteDm ? () => onDeleteDm(d.channel_id) : undefined
                  }
                  className={row}
                />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
