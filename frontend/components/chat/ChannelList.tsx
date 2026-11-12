"use client";
/**
 * @file components/chat/ChannelList.tsx
 * @brief Sidebar list of channels + DM threads. Highlights active item,
 *        shows unread badge per channel.
 */
import * as React from "react";
import { Trash2 } from "lucide-react";
import { motion } from "framer-motion";
import { fadeInOut, useMotionProps } from "@/components/ui/motion";
import { Avatar, Badge, IconButton, Skeleton } from "@/components/ui";
import type { ChatChannel, DmThread } from "@/lib/api/chat";

export interface ChannelListProps {
  channels: ChatChannel[];
  dms: DmThread[];
  activeId: string | null;
  unread: Record<string, number>;
  onSelect: (channelId: string) => void;
  onDeleteDm?: (channelId: string) => void;
  loading?: boolean;
}

/**
 * @brief One selectable conversation row; delete shows on hover/focus.
 * @return row element
 */
function ChannelRow({
  active,
  unread,
  primary,
  secondary,
  avatar,
  onClick,
  onDelete,
}: {
  active: boolean;
  unread: number;
  primary: string;
  secondary?: string;
  avatar: React.ReactNode;
  onClick: () => void;
  onDelete?: () => void;
}) {
  return (
    <div
      className={`group relative flex min-h-12 items-center gap-3 rounded-xl px-3 py-2 hover:bg-surface focus-within:bg-surface ${
        active ? "bg-surface" : ""
      }`}
    >
      <button
        type="button"
        onClick={onClick}
        aria-current={active ? "true" : undefined}
        className="flex min-w-0 flex-1 items-center gap-3 rounded-lg text-left outline-none after:absolute after:inset-0 after:content-[''] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        {avatar}
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold">
            {primary}
          </span>
          {secondary && (
            <span className="text-muted block truncate text-xs">
              {secondary}
            </span>
          )}
        </span>
        {unread > 0 && <Badge tone="accent">{unread}</Badge>}
      </button>
      {onDelete && (
        <IconButton
          aria-label="Delete conversation"
          size="sm"
          variant="ghost"
          className="relative z-10 size-11 opacity-100 md:size-8 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100"
          onClick={onDelete}
        >
          <Trash2 className="size-4" aria-hidden="true" />
        </IconButton>
      )}
    </div>
  );
}

export function ChannelList({
  channels,
  dms,
  activeId,
  unread,
  onSelect,
  onDeleteDm,
  loading,
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

  const grouped = channels.filter((c) => c.channel_type !== "direct");

  return (
    <div className="flex flex-col gap-4 p-2">
      <section aria-label="Channels" className="flex flex-col gap-1">
        <h2 className="text-muted px-3 pb-1 text-sm font-semibold">Channels</h2>
        {grouped.length === 0 && (
          <p className="text-muted px-3 text-xs">No channels</p>
        )}
        {grouped.map((c) => (
          <ChannelRow
            key={c.id}
            active={activeId === c.id}
            unread={unread[c.id] ?? 0}
            primary={`# ${c.name}`}
            secondary={c.channel_type}
            avatar={<Avatar size="md" name={c.name} />}
            onClick={() => onSelect(c.id)}
          />
        ))}
      </section>

      <section aria-label="Direct messages" className="flex flex-col gap-1">
        <h2 className="text-muted px-3 pb-1 text-sm font-semibold">
          Direct messages
        </h2>
        {dms.length === 0 && (
          <p className="text-muted px-3 text-xs">No conversations</p>
        )}
        {dms.map((d) => (
          <ChannelRow
            key={d.channel_id}
            active={activeId === d.channel_id}
            unread={unread[d.channel_id] ?? 0}
            primary={d.peer.display_name}
            secondary={`@${d.peer.username}`}
            avatar={
              <Avatar
                src={d.peer.avatar_url ?? undefined}
                size="md"
                name={d.peer.display_name}
              />
            }
            onClick={() => onSelect(d.channel_id)}
            onDelete={onDeleteDm ? () => onDeleteDm(d.channel_id) : undefined}
          />
        ))}
      </section>
    </div>
  );
}
