"use client";
/**
 * @file components/chat/ChatLauncher.tsx
 * @brief Chat launcher drawer listing recent channels + DMs. Opened via
 *        useChatDock.launcherOpen. Desktop: right drawer; mobile: bottom.
 *        Selecting a thread calls useChatDock.openThread.
 */
import * as React from "react";
import { Avatar, Skeleton, Drawer } from "@/components/ui";
import { useChatDock } from "@/stores/chatDock";
import { useChannels, useDmThreads, useChatRealtime } from "@/hooks/useChat";
import { useIsMobile } from "@/hooks/useIsMobile";
import type { ChatChannel, DmThread } from "@/lib/api/chat";

interface RowProps {
  id: string;
  name: string;
  label: string;
  src?: string;
  unread: number;
  onSelect: (id: string) => void;
}

/** @brief One selectable thread row with unread dot. */
function Row({ id, name, label, src, unread, onSelect }: RowProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(id)}
      aria-label={label}
      className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm outline-none hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      <Avatar size="sm" name={name} src={src} />
      <span className="min-w-0 flex-1 truncate">{name}</span>
      {unread > 0 && (
        <span
          role="img"
          aria-label={`${unread} unread`}
          className="size-2 shrink-0 rounded-full bg-accent"
        />
      )}
    </button>
  );
}

interface ThreadListProps {
  channels: ChatChannel[];
  dms: DmThread[];
  unread: Record<string, number>;
  isLoading: boolean;
  onSelect: (id: string) => void;
}

/** @brief Grouped channel and DM lists. */
function ThreadList({
  channels,
  dms,
  unread,
  isLoading,
  onSelect,
}: ThreadListProps) {
  const grouped = channels.filter((c) => c.channel_type !== "direct");
  if (isLoading) {
    return (
      <div className="flex min-w-56 flex-col gap-1 p-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={36} />
        ))}
      </div>
    );
  }
  if (grouped.length === 0 && dms.length === 0) {
    return <p className="p-3 text-sm text-muted">No conversations yet</p>;
  }
  return (
    <div className="flex min-w-56 flex-col gap-1">
      {grouped.length > 0 && (
        <>
          <h3 className="px-2 pt-1 text-xs font-semibold text-muted">
            Channels
          </h3>
          {grouped.map((c) => (
            <Row
              key={c.id}
              id={c.id}
              name={`# ${c.name}`}
              label={`Open channel ${c.name}`}
              unread={unread[c.id] ?? 0}
              onSelect={onSelect}
            />
          ))}
        </>
      )}
      {dms.length > 0 && (
        <>
          <h3 className="px-2 pt-1 text-xs font-semibold text-muted">
            Direct messages
          </h3>
          {dms.map((d) => (
            <Row
              key={d.channel_id}
              id={d.channel_id}
              name={d.peer.display_name}
              label={`Open conversation with ${d.peer.display_name}`}
              src={d.peer.avatar_url ?? undefined}
              unread={unread[d.channel_id] ?? 0}
              onSelect={onSelect}
            />
          ))}
        </>
      )}
    </div>
  );
}

/**
 * @brief Drawer with recent channels + DMs; driven by useChatDock.
 * @return drawer element
 */
export function ChatLauncher() {
  const launcherOpen = useChatDock((s) => s.launcherOpen);
  const setLauncherOpen = useChatDock((s) => s.setLauncherOpen);
  const openThread = useChatDock((s) => s.openThread);
  const isMobile = useIsMobile();
  const { data: channels = [], isLoading: chLoading } = useChannels();
  const { data: dms = [], isLoading: dmLoading } = useDmThreads();
  const { unread } = useChatRealtime();

  const handleSelect = (id: string) => {
    openThread(id);
    setLauncherOpen(false);
  };

  return (
    <Drawer
      open={launcherOpen}
      onClose={() => setLauncherOpen(false)}
      side={isMobile ? "bottom" : "right"}
      title="Chat"
    >
      <ThreadList
        channels={channels}
        dms={dms}
        unread={unread}
        isLoading={chLoading || dmLoading}
        onSelect={handleSelect}
      />
    </Drawer>
  );
}
