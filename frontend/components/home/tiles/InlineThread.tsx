"use client";
/**
 * @file components/home/tiles/InlineThread.tsx
 * @brief Last 3 messages of a thread plus a pill reply input.
 */
import * as React from "react";
import { Send } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { qk } from "@/lib/query-keys";
import { markChannelRead, type ChatMessage } from "@/lib/api/chat";
import type { HomeChatThread } from "@/lib/api/home";
import {
  useMessages,
  sendChatMessage,
  optimisticAddMessage,
} from "@/hooks/useChat";
import { useSession } from "@/stores/session";

/**
 * @brief Inline conversation preview with reply form.
 * @param thread Home chat thread being shown
 * @return thread body
 */
export function InlineThread({ thread }: { thread: HomeChatThread }) {
  const qc = useQueryClient();
  const reduce = useReducedMotion();
  const selfId = useSession((s) => s.user?.id ?? null);
  const { data } = useMessages(thread.channel_id, 3);
  const [text, setText] = React.useState("");

  // pages are newest-first: take newest 3, show oldest -> newest
  const messages = React.useMemo(
    () =>
      (data?.pages.flatMap((p) => p.items) ?? [])
        .filter((m) => !m.deleted)
        .slice(0, 3)
        .reverse(),
    [data],
  );

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const content = text.trim();
    if (!content) return;
    const optimistic: ChatMessage = {
      id: `optimistic-${Date.now()}`,
      channel_id: thread.channel_id,
      author: selfId
        ? { id: selfId, username: "", display_name: "", avatar_url: null }
        : null,
      content,
      edited_at: null,
      deleted: false,
      created_at: new Date().toISOString(),
    };
    optimisticAddMessage(qc, thread.channel_id, optimistic);
    sendChatMessage(thread.channel_id, content);
    setText("");
    void Promise.resolve(markChannelRead(thread.channel_id)).then(() =>
      qc.invalidateQueries({ queryKey: qk.home.chats() }),
    );
  };

  return (
    <div className="flex flex-col">
      <ul className="flex flex-col justify-end gap-2.5 overflow-hidden px-3.5 pb-2.5 pt-1">
        <AnimatePresence initial={false}>
          {messages.map((m) => {
            const mine = selfId !== null && m.author?.id === selfId;
            return (
              <motion.li
                key={m.id}
                initial={reduce ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduce ? undefined : { opacity: 0 }}
                className={cn("flex max-w-[88%] list-none", mine && "self-end")}
              >
                <div
                  className={cn(
                    "px-3 py-2 text-[13.5px] leading-snug",
                    mine
                      ? "rounded-[18px_18px_6px_18px] bg-surface-strong text-bg"
                      : "rounded-[18px_18px_18px_6px] bg-[var(--nx-bubble)]",
                  )}
                >
                  {!mine && m.author?.display_name ? (
                    <small className="mb-0.5 block text-[11.5px] text-[var(--nx-muted)]">
                      {m.author.display_name}
                    </small>
                  ) : null}
                  {m.content}
                </div>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ul>
      <form
        onSubmit={submit}
        className="mx-2.5 mb-2.5 flex items-center gap-2 rounded-full bg-[var(--nx-glass-solid)] py-1.5 pl-4 pr-1.5"
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-label={`Reply to ${thread.name}`}
          placeholder={`Reply to ${thread.name}`}
          autoComplete="off"
          className="min-w-0 flex-1 bg-transparent text-[13.5px] outline-none placeholder:text-[var(--nx-faint)]"
        />
        <button
          type="submit"
          aria-label="Send"
          className="grid h-9 w-9 place-items-center rounded-full bg-surface-strong text-bg"
        >
          <Send className="h-4 w-4" aria-hidden />
        </button>
      </form>
    </div>
  );
}
