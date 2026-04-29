"use client";
/**
 * @file components/chat/ChatLauncher.tsx
 * @brief Floating chat launcher pill. Desktop: click toggles an inline
 *        popover listing recent channels + DMs. Mobile: opens bottom drawer.
 *        Calls useChatDock.openThread on thread selection.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import Stack from "@mui/joy/Stack";
import { ChatBubbleLeftRightIcon } from "@heroicons/react/24/outline";
import { Avatar } from "@/components/ui";
import { Drawer } from "@/components/ui/Drawer";
import { useChatDock } from "@/stores/chatDock";
import { useChannels, useDmThreads } from "@/hooks/useChat";
import type { ChatChannel, DmThread } from "@/lib/api/chat";

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

interface ThreadListProps {
  channels: ChatChannel[];
  dms: DmThread[];
  onSelect: (id: string) => void;
}

function ThreadList({ channels, dms, onSelect }: ThreadListProps) {
  const grouped = channels.filter((c) => c.channel_type !== "direct");
  return (
    <Stack spacing={0.5} sx={{ minWidth: 220 }}>
      {grouped.length > 0 && (
        <>
          <Typography
            level="body-xs"
            textColor="text.tertiary"
            sx={{ px: 1, pt: 0.5 }}
          >
            Channels
          </Typography>
          {grouped.map((c) => (
            <Box
              key={c.id}
              role="button"
              tabIndex={0}
              onClick={() => onSelect(c.id)}
              onKeyDown={(e) =>
                (e.key === "Enter" || e.key === " ") && onSelect(c.id)
              }
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                px: 1.5,
                py: 0.75,
                borderRadius: "sm",
                cursor: "pointer",
                "&:hover": { bgcolor: "background.level1" },
                outline: "none",
                "&:focus-visible": { boxShadow: "sm" },
              }}
              aria-label={`Open channel ${c.name}`}
            >
              <Avatar size="sm">{c.name.charAt(0).toUpperCase()}</Avatar>
              <Typography level="body-sm" noWrap>
                # {c.name}
              </Typography>
            </Box>
          ))}
        </>
      )}
      {dms.length > 0 && (
        <>
          <Typography
            level="body-xs"
            textColor="text.tertiary"
            sx={{ px: 1, pt: 0.5 }}
          >
            Direct messages
          </Typography>
          {dms.map((d) => (
            <Box
              key={d.channel_id}
              role="button"
              tabIndex={0}
              onClick={() => onSelect(d.channel_id)}
              onKeyDown={(e) =>
                (e.key === "Enter" || e.key === " ") && onSelect(d.channel_id)
              }
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                px: 1.5,
                py: 0.75,
                borderRadius: "sm",
                cursor: "pointer",
                "&:hover": { bgcolor: "background.level1" },
                outline: "none",
                "&:focus-visible": { boxShadow: "sm" },
              }}
              aria-label={`Open conversation with ${d.peer.display_name}`}
            >
              <Avatar src={d.peer.avatar_url ?? undefined} size="sm">
                {d.peer.display_name.charAt(0)}
              </Avatar>
              <Typography level="body-sm" noWrap>
                {d.peer.display_name}
              </Typography>
            </Box>
          ))}
        </>
      )}
      {grouped.length === 0 && dms.length === 0 && (
        <Typography level="body-sm" textColor="text.tertiary" sx={{ p: 1.5 }}>
          No conversations yet
        </Typography>
      )}
    </Stack>
  );
}

/**
 * @brief Launcher pill + popover (desktop) or bottom drawer (mobile).
 */
export function ChatLauncher() {
  const launcherOpen = useChatDock((s) => s.launcherOpen);
  const unreadCount = useChatDock((s) => s.unreadCount);
  const setLauncherOpen = useChatDock((s) => s.setLauncherOpen);
  const openThread = useChatDock((s) => s.openThread);

  const isMobile = useIsMobile();
  const anchorRef = React.useRef<HTMLButtonElement | null>(null);

  const { data: channels = [] } = useChannels();
  const { data: dms = [] } = useDmThreads();

  const toggle = () => setLauncherOpen(!launcherOpen);

  const handleSelect = (id: string) => {
    openThread(id);
    setLauncherOpen(false);
  };

  const pill = (
    <Box sx={{ position: "relative" }}>
      <Box
        component="button"
        ref={anchorRef}
        onClick={toggle}
        aria-label="Open chat"
        aria-expanded={launcherOpen}
        aria-haspopup="true"
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          px: 2,
          py: 1,
          borderRadius: "xl",
          bgcolor: "primary.500",
          color: "white",
          border: "none",
          cursor: "pointer",
          fontFamily: "inherit",
          fontSize: "sm",
          fontWeight: "md",
          boxShadow: "md",
          "&:hover": { bgcolor: "primary.600" },
          "&:focus-visible": {
            outline: "2px solid",
            outlineColor: "primary.300",
            outlineOffset: 2,
          },
        }}
      >
        <ChatBubbleLeftRightIcon width={18} />
        <span>Chat</span>
        {unreadCount > 0 && (
          <Box
            sx={{
              ml: 0.5,
              bgcolor: "danger.500",
              color: "white",
              borderRadius: "xl",
              fontSize: "0.65rem",
              fontWeight: "lg",
              px: 0.75,
              py: 0.1,
              lineHeight: 1.4,
            }}
            aria-label={`${unreadCount} unread messages`}
          >
            {unreadCount}
          </Box>
        )}
      </Box>

      {/* Desktop popover */}
      {!isMobile && launcherOpen && (
        <Box
          role="dialog"
          aria-label="Chat thread list"
          sx={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            right: 0,
            bgcolor: "background.surface",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: "md",
            boxShadow: "lg",
            p: 1,
            zIndex: 1300,
            minWidth: 240,
            maxHeight: 400,
            overflowY: "auto",
          }}
        >
          <ThreadList channels={channels} dms={dms} onSelect={handleSelect} />
        </Box>
      )}
    </Box>
  );

  if (isMobile) {
    return (
      <>
        {pill}
        <Drawer
          open={launcherOpen}
          onClose={() => setLauncherOpen(false)}
          side="bottom"
          title="Chat"
        >
          <ThreadList channels={channels} dms={dms} onSelect={handleSelect} />
        </Drawer>
      </>
    );
  }

  return pill;
}
