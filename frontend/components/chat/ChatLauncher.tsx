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
 * @brief Right-side slide-out drawer with the recent channels + DMs.
 *        Triggered externally via useChatDock.launcherOpen (RightRail tab).
 *        Desktop: right drawer. Mobile: bottom drawer.
 */
export function ChatLauncher() {
  const launcherOpen = useChatDock((s) => s.launcherOpen);
  const setLauncherOpen = useChatDock((s) => s.setLauncherOpen);
  const openThread = useChatDock((s) => s.openThread);

  const isMobile = useIsMobile();

  const { data: channels = [], isLoading: chLoading } = useChannels();
  const { data: dms = [], isLoading: dmLoading } = useDmThreads();
  const { unread } = useChatRealtime();
  const isLoading = chLoading || dmLoading;

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
      width={360}
    >
      <Box sx={{ p: 1 }}>
        <ThreadList
          channels={channels}
          dms={dms}
          unread={unread}
          isLoading={isLoading}
          onSelect={handleSelect}
        />
      </Box>
    </Drawer>
  );
}
