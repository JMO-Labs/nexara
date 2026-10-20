"use client";
/**
 * @file components/feed/PostHeader.tsx
 * @brief Avatar + author identity + relative time + overflow menu.
 */
import * as React from "react";
import Box from "@mui/joy/Box";
import Stack from "@mui/joy/Stack";
import Typography from "@mui/joy/Typography";
import Menu from "@mui/joy/Menu";
import MenuItem from "@mui/joy/MenuItem";
import MenuButton from "@mui/joy/MenuButton";
import Dropdown from "@mui/joy/Dropdown";
import { EllipsisHorizontalIcon } from "@heroicons/react/24/outline";
import { formatDistanceToNowStrict } from "date-fns";
import { Avatar, IconButton } from "@/components/ui";
import type { Post } from "@/lib/api/posts";

export interface PostHeaderProps {
  post: Post;
  isAuthor: boolean;
  isAdmin?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function PostHeader({
  post,
  isAuthor,
  isAdmin,
  onEdit,
  onDelete,
}: PostHeaderProps) {
  const showMenu = isAuthor || isAdmin;
  const time = React.useMemo(() => {
    try {
      return formatDistanceToNowStrict(new Date(post.created_at), {
        addSuffix: true,
      });
    } catch {
      return "";
    }
  }, [post.created_at]);

  return (
    <Stack direction="row" spacing={1.5} alignItems="center">
      <Avatar src={post.author.avatar_url ?? undefined} size="md">
        {post.author.display_name.charAt(0)}
      </Avatar>
      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Typography level="title-sm" sx={{ fontFamily: "display" }}>
          {post.author.display_name}
        </Typography>
        <Typography level="body-xs" textColor="text.tertiary">
          @{post.author.username} · {time}
          {post.updated_at !== post.created_at ? " · edited" : ""}
        </Typography>
      </Box>
      {showMenu ? (
        <Dropdown>
          <MenuButton slots={{ root: IconButton }} aria-label="Post options">
            <EllipsisHorizontalIcon width={20} />
          </MenuButton>
          <Menu placement="bottom-end" size="sm">
            {isAuthor && onEdit ? (
              <MenuItem onClick={onEdit}>Edit</MenuItem>
            ) : null}
            {(isAuthor || isAdmin) && onDelete ? (
              <MenuItem color="danger" onClick={onDelete}>
                Delete
              </MenuItem>
            ) : null}
          </Menu>
        </Dropdown>
      ) : null}
    </Stack>
  );
}

export default PostHeader;
