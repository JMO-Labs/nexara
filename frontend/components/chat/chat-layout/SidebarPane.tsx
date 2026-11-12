"use client";
/**
 * @file components/chat/chat-layout/SidebarPane.tsx
 * @brief Left pane: new-DM button, mute toggle and the channel/DM list.
 */
import { Bell, BellOff, SquarePen } from "lucide-react";
import { Button, IconButton } from "@/components/ui";
import { ChannelList, type ChannelListProps } from "../ChannelList";

export interface SidebarPaneProps extends ChannelListProps {
  muted: boolean;
  onToggleMute: () => void;
  onNewDm: () => void;
  /** Extra classes (visibility per breakpoint). */
  className?: string;
}

/**
 * @brief Channel list column.
 * @param props list props plus mute/new-DM handlers
 * @return aside element
 */
export function SidebarPane({
  muted,
  onToggleMute,
  onNewDm,
  className = "",
  ...list
}: SidebarPaneProps) {
  return (
    <aside
      aria-label="Conversations"
      className={`min-h-0 flex-col border-border md:border-r ${className}`}
    >
      <div className="flex shrink-0 items-center gap-2 border-b border-border p-2">
        <h1 className="sr-only">Chat</h1>
        <Button
          size="md"
          variant="primary"
          className="min-h-11 flex-1"
          onClick={onNewDm}
        >
          <SquarePen className="size-4" aria-hidden="true" />
          New direct message
        </Button>
        <IconButton
          aria-label={
            muted ? "Unmute chat notifications" : "Mute chat notifications"
          }
          aria-pressed={muted}
          variant={muted ? "secondary" : "ghost"}
          className="size-11"
          onClick={onToggleMute}
        >
          {muted ? (
            <BellOff className="size-5" aria-hidden="true" />
          ) : (
            <Bell className="size-5" aria-hidden="true" />
          )}
        </IconButton>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        <ChannelList {...list} />
      </div>
    </aside>
  );
}
