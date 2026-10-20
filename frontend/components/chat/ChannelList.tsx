"use client";
/**
 * @file components/chat/ChannelList.tsx
 * @brief Sidebar list of channels + DM threads. Highlights active item,
 *        shows unread badge per channel.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Box from "@mui/joy/Box";
import { TrashIcon } from "@heroicons/react/24/outline";
import { Avatar, Badge, IconButton, Skeleton } from "@/components/ui";
import type { ChatChannel, DmThread } from "@/lib/api/chat";

export interface ChannelListProps {
  channels: ChatChannel[];
  dms: DmThread[];
  activeId: string | null;
  unread: Record<string, number>;
  onSelect: (channelId: string) => void;
  onDeleteDm?: (channelId: string) => void;
  loading?: boolean;
}

function ChannelRow({
  active,
  unread,
  primary,
  secondary,
  avatar,
  onClick,
  onDelete,
}: {
  active: boolean;
  unread: number;
  primary: string;
  secondary?: string;
  avatar: React.ReactNode;
  onClick: () => void;
  onDelete?: () => void;
}) {
  const [hover, setHover] = React.useState(false);
  return (
    <Box
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onClick()}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.25,
        px: 1.25,
        py: 1,
        borderRadius: "md",
        cursor: "pointer",
        bgcolor: active ? "background.level1" : "transparent",
        "&:hover": { bgcolor: "background.level1" },
        outline: "none",
        "&:focus-visible": { boxShadow: "sm" },
      }}
    >
      {avatar}
      <Stack sx={{ flex: 1, minWidth: 0 }}>
        <Typography level="title-sm" noWrap>
          {primary}
        </Typography>
        {secondary && (
          <Typography level="body-xs" textColor="text.tertiary" noWrap>
            {secondary}
          </Typography>
        )}
      </Stack>
      {unread > 0 && <Badge>{unread}</Badge>}
      {onDelete && hover && (
        <IconButton
          aria-label="Delete conversation"
          size="sm"
          variant="plain"
          color="danger"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
        >
          <TrashIcon width={14} />
        </IconButton>
      )}
    </Box>
  );
}

export function ChannelList({
  channels,
  dms,
  activeId,
  unread,
  onSelect,
  onDeleteDm,
  loading,
}: ChannelListProps) {
  if (loading) {
    return (
      <Stack spacing={1} p={1}>
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} height={48} />
        ))}
      </Stack>
    );
  }

  const grouped = channels.filter((c) => c.channel_type !== "direct");

  return (
    <Stack spacing={2} p={1}>
      <Stack spacing={0.5}>
        <Typography
          level="title-sm"
          textColor="text.tertiary"
          sx={{ px: 1.25, mb: 0.5 }}
        >
          Channels
        </Typography>
        {grouped.length === 0 && (
          <Typography
            level="body-xs"
            textColor="text.tertiary"
            sx={{ px: 1.25 }}
          >
            No channels
          </Typography>
        )}
        {grouped.map((c) => (
          <ChannelRow
            key={c.id}
            active={activeId === c.id}
            unread={unread[c.id] ?? 0}
            primary={`# ${c.name}`}
            secondary={c.channel_type}
            avatar={<Avatar size="sm">{c.name.charAt(0).toUpperCase()}</Avatar>}
            onClick={() => onSelect(c.id)}
          />
        ))}
      </Stack>

      <Stack spacing={0.5}>
        <Typography
          level="title-sm"
          textColor="text.tertiary"
          sx={{ px: 1.25, mb: 0.5 }}
        >
          Direct messages
        </Typography>
        {dms.length === 0 && (
          <Typography
            level="body-xs"
            textColor="text.tertiary"
            sx={{ px: 1.25 }}
          >
            No conversations
          </Typography>
        )}
        {dms.map((d) => (
          <ChannelRow
            key={d.channel_id}
            active={activeId === d.channel_id}
            unread={unread[d.channel_id] ?? 0}
            primary={d.peer.display_name}
            secondary={`@${d.peer.username}`}
            avatar={
              <Avatar src={d.peer.avatar_url ?? undefined} size="sm">
                {d.peer.display_name.charAt(0)}
              </Avatar>
            }
            onClick={() => onSelect(d.channel_id)}
            onDelete={onDeleteDm ? () => onDeleteDm(d.channel_id) : undefined}
          />
        ))}
      </Stack>
    </Stack>
  );
}
