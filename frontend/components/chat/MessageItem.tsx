"use client";
/**
 * @file components/chat/MessageItem.tsx
 * @brief Single chat message row: avatar, author, time, body.
 *        Avatar/name click opens a menu (View, Send DM). Hover row
 *        reveals a Reply action that bubbles up via onReply.
 */
import * as React from "react";
import Stack from "@mui/joy/Stack";
import Box from "@mui/joy/Box";
import Typography from "@mui/joy/Typography";
import Menu from "@mui/joy/Menu";
import MenuItem from "@mui/joy/MenuItem";
import Dropdown from "@mui/joy/Dropdown";
import MenuButton from "@mui/joy/MenuButton";
import { format } from "date-fns";
import {
  ArrowUturnLeftIcon,
  ChatBubbleLeftRightIcon,
} from "@heroicons/react/24/outline";
import { Avatar, IconButton, Markdown } from "@/components/ui";
import type { ChatMessage } from "@/lib/api/chat";

export interface MessageItemProps {
  message: ChatMessage;
  /** Compact mode hides avatar/name when grouping consecutive messages. */
  compact?: boolean;
  /** True when this message belongs to the active session user. */
  isSelf?: boolean;
  onReply?: (message: ChatMessage) => void;
  onSendDm?: (userId: string) => void;
}

export function MessageItem({
  message,
  compact,
  isSelf,
  onReply,
  onSendDm,
}: MessageItemProps) {
  const [hover, setHover] = React.useState(false);

  const time = (() => {
    try {
      return format(new Date(message.created_at), "p");
    } catch {
      return "";
    }
  })();

  const name = message.author?.display_name ?? "Unknown";
  const initial = name.charAt(0);
  const deleted = message.deleted;
  const authorId = message.author?.id;

  const avatar = (
    <Avatar size="sm" src={message.author?.avatar_url ?? undefined}>
      {initial}
    </Avatar>
  );

  const authorBlock =
    authorId && !isSelf ? (
      <Dropdown>
        <MenuButton
          slots={{ root: "span" }}
          slotProps={{
            root: {
              style: {
                cursor: "pointer",
                background: "none",
                border: 0,
                padding: 0,
              },
            },
          }}
        >
          {avatar}
        </MenuButton>
        <Menu placement="bottom-start" size="sm">
          <MenuItem onClick={() => onSendDm?.(authorId)} disabled={!onSendDm}>
            <ChatBubbleLeftRightIcon width={16} style={{ marginRight: 8 }} />
            Send DM
          </MenuItem>
        </Menu>
      </Dropdown>
    ) : (
      avatar
    );

  return (
    <Stack
      direction="row"
      spacing={1.5}
      alignItems="flex-start"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      sx={{
        px: 2,
        py: compact ? 0.25 : 0.75,
        position: "relative",
        "&:hover": { bgcolor: "background.level1" },
        opacity: message.id.startsWith("optimistic-") ? 0.6 : 1,
      }}
    >
      <Stack sx={{ width: 36 }}>{!compact && authorBlock}</Stack>
      <Stack sx={{ flex: 1, minWidth: 0 }}>
        {!compact && (
          <Stack direction="row" spacing={1} alignItems="baseline">
            <Typography level="title-sm">{name}</Typography>
            <Typography level="body-xs" textColor="text.tertiary">
              {time}
              {message.edited_at && " (edited)"}
            </Typography>
          </Stack>
        )}
        {deleted ? (
          <Typography
            level="body-sm"
            sx={{ color: "text.tertiary", fontStyle: "italic" }}
          >
            {message.content}
          </Typography>
        ) : (
          <Box sx={{ fontSize: "0.875rem" }}>
            <Markdown content={message.content} size="sm" />
          </Box>
        )}
      </Stack>

      {hover && !deleted && onReply && (
        <Box
          sx={{
            position: "absolute",
            right: 8,
            top: 4,
            bgcolor: "background.surface",
            borderRadius: "sm",
            boxShadow: "sm",
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <IconButton
            aria-label="Reply"
            size="sm"
            variant="plain"
            onClick={() => onReply(message)}
          >
            <ArrowUturnLeftIcon width={14} />
          </IconButton>
        </Box>
      )}
    </Stack>
  );
}
