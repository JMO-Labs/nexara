"use client";
/**
 * @file components/chat/ChatLauncher.tsx
 * @brief Floating chat launcher pill. Desktop: click toggles an inline
 *        popover (role=menu) listing recent channels + DMs. Mobile: opens
 *        bottom drawer. Calls useChatDock.openThread on thread selection.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import Stack from "@mui/joy/Stack";
import { Skeleton } from "@mui/joy";
import { ChatBubbleLeftRightIcon } from "@heroicons/react/24/outline";
import { Avatar } from "@/components/ui";
import { Drawer } from "@/components/ui/Drawer";
import { useChatDock } from "@/stores/chatDock";
import { useChannels, useDmThreads, useChatRealtime } from "@/hooks/useChat";
import { useIsMobile } from "@/hooks/useIsMobile";
import type { ChatChannel, DmThread } from "@/lib/api/chat";

interface ThreadListProps {
  channels: ChatChannel[];
  dms: DmThread[];
  unread: Record<string, number>;
  isLoading: boolean;
  onSelect: (id: string) => void;
}

function ThreadList({
  channels,
  dms,
  unread,
  isLoading,
  onSelect,
}: ThreadListProps) {
  const grouped = channels.filter((c) => c.channel_type !== "direct");
  const firstItemRef = React.useRef<HTMLDivElement | null>(null);

  // Fix 5: auto-focus first item when list mounts
  React.useEffect(() => {
    firstItemRef.current?.focus();
  }, []);

  // Fix 9: show skeleton rows while loading
  if (isLoading) {
    return (
      <Stack spacing={0.5} sx={{ minWidth: 220, p: 1 }}>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} variant="rectangular" height={36} />
        ))}
      </Stack>
    );
  }

  const allEmpty = grouped.length === 0 && dms.length === 0;

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
          {grouped.map((c, i) => (
            <Box
              key={c.id}
              ref={i === 0 && dms.length === 0 ? firstItemRef : undefined}
              role="menuitem"
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
              <Typography level="body-sm" noWrap sx={{ flex: 1 }}>
                # {c.name}
              </Typography>
              {/* Fix 10: unread dot */}
              {(unread[c.id] ?? 0) > 0 && (
                <Box
                  aria-label={`${unread[c.id]} unread`}
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: "danger.500",
                    flexShrink: 0,
                  }}
                />
              )}
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
          {dms.map((d, i) => (
            <Box
              key={d.channel_id}
              ref={i === 0 ? firstItemRef : undefined}
              role="menuitem"
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
              <Typography level="body-sm" noWrap sx={{ flex: 1 }}>
                {d.peer.display_name}
              </Typography>
              {/* Fix 10: unread dot */}
              {(unread[d.channel_id] ?? 0) > 0 && (
                <Box
                  aria-label={`${unread[d.channel_id]} unread`}
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: "danger.500",
                    flexShrink: 0,
                  }}
                />
              )}
            </Box>
          ))}
        </>
      )}
      {allEmpty && (
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
  // Fix 5: stable ref on pill for focus restoration
  const pillRef = React.useRef<HTMLButtonElement | null>(null);
  const popoverRef = React.useRef<HTMLDivElement | null>(null);

  const { data: channels = [], isLoading: chLoading } = useChannels();
  const { data: dms = [], isLoading: dmLoading } = useDmThreads();
  const { unread } = useChatRealtime();
  const isLoading = chLoading || dmLoading;

  const toggle = () => setLauncherOpen(!launcherOpen);

  const handleSelect = (id: string) => {
    openThread(id);
    setLauncherOpen(false);
  };

  // Fix 5: outside-click closes popover
  React.useEffect(() => {
    if (!launcherOpen || isMobile) return;
    const handler = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        pillRef.current &&
        !pillRef.current.contains(e.target as Node)
      ) {
        setLauncherOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [launcherOpen, isMobile, setLauncherOpen]);

  const pill = (
    <Box sx={{ position: "relative" }}>
      <Box
        component="button"
        ref={pillRef}
        id="chat-launcher-pill"
        onClick={toggle}
        aria-label="Open chat"
        aria-expanded={launcherOpen}
        aria-haspopup="menu"
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

      {/* Fix 5: role=menu, z-index 1250 (Fix 11), Escape closes */}
      {!isMobile && launcherOpen && (
        <Box
          ref={popoverRef}
          role="menu"
          aria-label="Chat thread list"
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setLauncherOpen(false);
              pillRef.current?.focus();
            }
          }}
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
            zIndex: 1250, // Fix 11: below Joy Modal default 1300
            minWidth: 240,
            maxHeight: 400,
            overflowY: "auto",
          }}
        >
          <ThreadList
            channels={channels}
            dms={dms}
            unread={unread}
            isLoading={isLoading}
            onSelect={handleSelect}
          />
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
          <ThreadList
            channels={channels}
            dms={dms}
            unread={unread}
            isLoading={isLoading}
            onSelect={handleSelect}
          />
        </Drawer>
      </>
    );
  }

  return pill;
}
