"use client";
/**
 * @file components/chat/FloatingChatDock.tsx
 * @brief Floating mini-chat dock. Fixed bottom-right: a row of ChatHead
 *        cards + a ChatLauncher pill. Hidden on /app/chat route.
 *        Mobile: single bottom drawer (only one thread at a time).
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import { AnimatePresence, motion, type Variants } from "framer-motion";
import { usePathname } from "next/navigation";
import { useChatDock } from "@/stores/chatDock";
import { useChatRealtime } from "@/hooks/useChat";
import { ChatHead } from "./ChatHead";
import { ChatLauncher } from "./ChatLauncher";
import { Drawer } from "@/components/ui/Drawer";
import { spring, fast } from "@/components/ui/motion";

// Slide-from-bottom variant for chat head cards
const chatHeadVariants: Variants = {
  hidden: { opacity: 0, y: 40 },
  show: { opacity: 1, y: 0, transition: spring },
  exit: { opacity: 0, y: 40, transition: fast },
};

function useIsMobile(): boolean {
  const [mobile, setMobile] = React.useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia("(max-width: 767px)").matches,
  );
  React.useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const handler = (e: MediaQueryListEvent) => setMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);
  return mobile;
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

export function FloatingChatDock() {
  const pathname = usePathname();
  const openThreadIds = useChatDock((s) => s.openThreadIds);
  const launcherOpen = useChatDock((s) => s.launcherOpen);
  const setLauncherOpen = useChatDock((s) => s.setLauncherOpen);
  const isMobile = useIsMobile();

  // Do not render on the full chat page — it would be redundant.
  if (pathname.startsWith("/app/chat")) return null;

  if (isMobile) {
    // Mobile: single bottom drawer; show most recently opened thread
    const activeId = openThreadIds[openThreadIds.length - 1] ?? null;
    return (
      <Box
        data-testid="floating-chat-dock"
        sx={{ position: "fixed", bottom: 16, right: 16, zIndex: 1200 }}
      >
        <UnreadSync />
        <ChatLauncher />
        {activeId && (
          <Drawer
            open={!launcherOpen && Boolean(activeId)}
            onClose={() => setLauncherOpen(true)}
            side="bottom"
            title="Chat"
          >
            <ChatHead threadId={activeId} label={activeId} />
          </Drawer>
        )}
      </Box>
    );
  }

  return (
    <Box
      data-testid="floating-chat-dock"
      sx={{
        position: "fixed",
        bottom: 16,
        right: 16,
        zIndex: 1200,
        display: "flex",
        flexDirection: "row",
        alignItems: "flex-end",
        gap: 1,
        pointerEvents: "none",
        "& > *": { pointerEvents: "auto" },
      }}
    >
      <UnreadSync />
      {/* Open chat heads — left to right */}
      <Stack direction="row" spacing={1} alignItems="flex-end">
        <AnimatePresence initial={false}>
          {openThreadIds.map((id) => (
            <motion.div
              key={id}
              variants={chatHeadVariants}
              initial="hidden"
              animate="show"
              exit="exit"
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-end",
              }}
            >
              <ChatHead threadId={id} label={id} />
            </motion.div>
          ))}
        </AnimatePresence>
      </Stack>

      {/* Launcher pill */}
      <ChatLauncher />
    </Box>
  );
}
