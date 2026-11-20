"use client";
/**
 * @file components/home/tiles/ChatsTile.tsx
 * @brief Chats tile: ranked threads, one open with inline reply.
 */
import * as React from "react";
import Link from "next/link";
import { MessageSquare } from "lucide-react";
import { HomeTile, type TileSlotProps } from "@/components/home/HomeTile";
import { ChatThreadRow } from "./ChatThreadRow";
import { InlineThread } from "./InlineThread";
import { useHomeChats } from "@/hooks/useHomeChats";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { markChannelRead } from "@/lib/api/chat";
import { inScope, useHomeScope } from "@/stores/homeScope";

/**
 * @brief Home chats tile.
 * @param props open/onToggle from the page accordion
 * @return tile element
 */
export function ChatsTile({ open, onToggle }: TileSlotProps) {
  const { data } = useHomeChats(4);
  const { data: groups } = useSubgroupList();
  const scope = useHomeScope((s) => s.scope);
  const [openId, setOpenId] = React.useState<string | null | undefined>(
    undefined,
  );

  const all = data?.items ?? [];
  const threads = all.filter((t) =>
    t.channel_type === "direct"
      ? scope === "all"
      : inScope(t.subgroup_id, scope),
  );
  const activeId =
    openId === undefined ? (threads[0]?.channel_id ?? null) : openId;

  const top = all[0]?.last_message;
  const summary = top
    ? `${top.author_name ? `${top.author_name}: ` : ""}${top.content}`
    : undefined;
  const count = all.reduce((n, t) => n + t.unread_count, 0);
  const hot = all.some((t) => t.mentions_me);

  const onRow = (id: string) => {
    if (id === activeId) return setOpenId(null);
    setOpenId(id);
    void markChannelRead(id);
  };

  const groupName = groups?.find((g) => g.id === scope)?.name ?? "this group";

  return (
    <HomeTile
      id="chat"
      title="Chats"
      icon={MessageSquare}
      href="/app/chat"
      linkLabel="See all chats"
      summary={summary}
      count={count}
      hot={hot}
      open={open}
      onToggle={onToggle}
      className="md:[grid-area:chat]"
    >
      {all.length === 0 ? (
        <div className="grid flex-1 place-content-center gap-2 py-8 text-center">
          <p className="font-medium">No chats yet</p>
          <Link href="/app/chat" className="text-sm underline">
            Start a chat
          </Link>
        </div>
      ) : threads.length === 0 ? (
        <p className="py-8 text-center text-[var(--nx-muted)]">
          Nothing from {groupName} yet
        </p>
      ) : (
        <ul className="m-0 flex max-h-[420px] flex-col gap-1.5 overflow-y-auto p-0 [&>li]:shrink-0">
          {threads.map((t) => (
            <ChatThreadRow
              key={t.channel_id}
              thread={t}
              open={t.channel_id === activeId}
              onOpen={() => onRow(t.channel_id)}
            >
              {t.channel_id === activeId ? <InlineThread thread={t} /> : null}
            </ChatThreadRow>
          ))}
        </ul>
      )}
      {all.length > 0 && (
        <div className="mt-auto flex flex-wrap items-center justify-end gap-2 pt-2">
          <Link
            href="/app/chat"
            className="inline-flex min-h-11 items-center rounded-full px-3 text-sm text-[var(--nx-muted)] hover:underline"
          >
            See all chats
          </Link>
          <Link
            href="/app/chat"
            className="inline-flex min-h-11 items-center rounded-full bg-surface-strong px-4 text-sm font-medium text-bg"
          >
            Start a chat
          </Link>
        </div>
      )}
    </HomeTile>
  );
}
