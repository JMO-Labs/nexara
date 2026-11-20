"use client";
/**
 * @file components/chat/chat-layout/SidebarPane.tsx
 * @brief Glass aside: New message pill, mute toggle, search, All/Groups/Direct
 *        segmented filter and the thread list.
 */
import * as React from "react";
import { Bell, BellOff, SquarePen } from "lucide-react";
import { IconButton } from "@/components/ui";
import { SearchField, Segmented } from "@/components/ui/page";
import { cn } from "@/lib/utils";
import {
  ChannelList,
  type ChannelListProps,
  type ChatSegment,
} from "../ChannelList";

export interface SidebarPaneProps extends Omit<
  ChannelListProps,
  "query" | "segment"
> {
  muted: boolean;
  onToggleMute: () => void;
  onNewDm: () => void;
  /** Extra classes (visibility per breakpoint). */
  className?: string;
}

const SEGMENTS: { value: ChatSegment; label: string }[] = [
  { value: "all", label: "All" },
  { value: "groups", label: "Groups" },
  { value: "direct", label: "Direct" },
];

/**
 * @brief Conversation list column.
 * @param props list props plus mute/new-message handlers
 * @return aside element
 */
export function SidebarPane({
  muted,
  onToggleMute,
  onNewDm,
  className = "",
  ...list
}: SidebarPaneProps) {
  const [query, setQuery] = React.useState("");
  const [segment, setSegment] = React.useState<ChatSegment>("all");
  return (
    <aside
      aria-label="Conversations"
      className={cn(
        "glass min-h-0 flex-col gap-3 rounded-[32px] p-4",
        className,
      )}
    >
      <h1 className="sr-only">Chat</h1>
      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          onClick={onNewDm}
          className="flex min-h-11 flex-1 items-center justify-center gap-2 rounded-full bg-surface-strong px-4 text-sm font-medium text-bg outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <SquarePen className="size-4" aria-hidden="true" />
          New message
        </button>
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
      <div className="flex shrink-0">
        <SearchField
          value={query}
          onChange={setQuery}
          placeholder="Search conversations"
          label="Search conversations"
        />
      </div>
      <Segmented
        options={SEGMENTS}
        value={segment}
        onChange={setSegment}
        label="Conversation filter"
      />
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-1">
        <ChannelList {...list} query={query} segment={segment} />
      </div>
    </aside>
  );
}
