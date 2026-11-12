"use client";
/**
 * @file components/chat/FloatingChatDock.tsx
 * @brief Floating mini-chat dock. Fixed bottom-right: a row of ChatHead
 *        cards + a ChatLauncher pill. Hidden on /app/chat route.
 *        Mobile: single bottom drawer (only one thread at a time).
 */
import * as React from "react";
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  type Variants,
} from "framer-motion";
import { usePathname } from "next/navigation";
import { useChatDock } from "@/stores/chatDock";
import { useChatRealtime, useChannels, useDmThreads } from "@/hooks/useChat";
import { useIsMobile } from "@/hooks/useIsMobile";

import { ChatHead } from "./ChatHead";
import { ChatLauncher } from "./ChatLauncher";
import { Drawer } from "@/components/ui/Drawer";
import { spring, fast } from "@/components/ui/motion";
import type { ChatChannel, DmThread } from "@/lib/api/chat";

/** Build slide-from-bottom variants; reduced-motion replaces y movement with a
 *  simple opacity fade so no positional animation occurs. */
function useChatHeadVariants(): Variants {
  const reduced = useReducedMotion();
  return {
    hidden: { opacity: 0, y: reduced ? 0 : 40 },
    show: { opacity: 1, y: 0, transition: reduced ? { duration: 0 } : spring },
    exit: {
      opacity: 0,
      y: reduced ? 0 : 40,
      transition: reduced ? { duration: 0 } : fast,
    },
  };
}

/**
 * @brief Syncs useChatRealtime unread totals → chatDock.unreadCount.
 *        Must be rendered inside FloatingChatDock so it only runs once.
 */
function UnreadSync() {
  const { unread } = useChatRealtime();
  const setUnreadCount = useChatDock((s) => s.setUnreadCount);
  React.useEffect(() => {
    const total = Object.values(unread).reduce((a, b) => a + b, 0);
    setUnreadCount(total);
  }, [unread, setUnreadCount]);
  return null;
}

/**
 * @brief Builds a Map<threadId, humanLabel> from channels + DM threads.
 *        Used to pass resolved names to ChatHead instead of raw UUIDs.
 */
function useLabelMap(
  channels: ChatChannel[],
  dms: DmThread[],
): Map<string, string> {
  return React.useMemo(() => {
    const map = new Map<string, string>();
    for (const c of channels) map.set(c.id, `# ${c.name}`);
    for (const d of dms) map.set(d.channel_id, d.peer.display_name);
    return map;
  }, [channels, dms]);
}

export function FloatingChatDock() {
  const chatHeadVariants = useChatHeadVariants();
  const pathname = usePathname();
  const openThreadIds = useChatDock((s) => s.openThreadIds);
  const launcherOpen = useChatDock((s) => s.launcherOpen);
  const closeThread = useChatDock((s) => s.closeThread);
  const isMobile = useIsMobile();

  const { data: channels = [] } = useChannels();
  const { data: dms = [] } = useDmThreads();
  const labelMap = useLabelMap(channels, dms);

  // Fix 1: exact match or subpath — do not hide on /app/chat-something
  if (pathname === "/app/chat" || pathname.startsWith("/app/chat/"))
    return null;

  if (isMobile) {
    // Mobile: single bottom drawer for active thread + launcher drawer
    const activeId = openThreadIds[openThreadIds.length - 1] ?? null;
    return (
      <div data-testid="floating-chat-dock">
        <UnreadSync />
        <ChatLauncher />
        {activeId && (
          <Drawer
            open={!launcherOpen && Boolean(activeId)}
            onClose={() => closeThread(activeId)}
            side="bottom"
            title="Chat"
          >
            <ChatHead
              threadId={activeId}
              label={labelMap.get(activeId) ?? "Conversation"}
            />
          </Drawer>
        )}
      </div>
    );
  }

  return (
    <div
      data-testid="floating-chat-dock"
      className="pointer-events-none fixed right-16 bottom-4 z-[1200] flex flex-row items-end gap-2 *:pointer-events-auto"
    >
      <UnreadSync />
      <ChatLauncher />
      {/* Open chat heads — left to right */}
      <div className="flex flex-row items-end gap-2">
        <AnimatePresence initial={false}>
          {openThreadIds.map((id) => (
            <motion.div
              key={id}
              variants={chatHeadVariants}
              initial="hidden"
              animate="show"
              exit="exit"
              className="flex flex-col items-end"
            >
              <ChatHead
                threadId={id}
                label={labelMap.get(id) ?? "Conversation"}
              />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
