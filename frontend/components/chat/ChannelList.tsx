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
  return (
    <ul className="flex list-none flex-col gap-2 p-0">
      {grouped.map((c) => (
        <li key={c.id}>
          <ThreadRow
            name={`# ${c.name}`}
            preview={c.channel_type}
            color={groupColor(c.subgroup_id, null)}
            unread={unread[c.id] ?? 0}
            selected={activeId === c.id}
            onClick={() => onSelect(c.id)}
            className={row}
          />
        </li>
      ))}
      {direct.map((d) => (
        <li key={d.channel_id}>
          <ThreadRow
            name={d.peer.display_name}
            preview={`@${d.peer.username}`}
            color="var(--nx-muted)"
            avatar={
              <Avatar
                src={d.peer.avatar_url ?? undefined}
                size="md"
                name={d.peer.display_name}
                userId={d.peer.id}
              />
            }
            unread={unread[d.channel_id] ?? 0}
            selected={activeId === d.channel_id}
            onClick={() => onSelect(d.channel_id)}
            onDelete={onDeleteDm ? () => onDeleteDm(d.channel_id) : undefined}
            className={row}
          />
        </li>
      ))}
    </ul>
  );
}
