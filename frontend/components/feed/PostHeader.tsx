"use client";
/**
 * @file components/feed/PostHeader.tsx
 * @brief Avatar + author identity + relative time + overflow menu.
 */
import * as React from "react";
import { MoreHorizontal } from "lucide-react";
import { formatDistanceToNowStrict } from "date-fns";
import { Avatar, IconButton } from "@/components/ui";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/shadcn/dropdown-menu";
import type { Post } from "@/lib/api/posts";

export interface PostHeaderProps {
  post: Post;
  isAuthor: boolean;
  isAdmin?: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
}

/**
 * @brief Post author row with edit/delete menu for authors and admins.
 * @param post the post
 * @param isAuthor viewer wrote the post
 * @param isAdmin viewer is admin/owner
 * @param onEdit edit handler (author only)
 * @param onDelete delete handler
 * @return header element
 */
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
    <div className="flex items-center gap-3">
      <Avatar
        src={post.author.avatar_url ?? undefined}
        name={post.author.display_name}
      />
      <div className="min-w-0 grow">
        <p className="truncate text-sm font-semibold text-ink">
          {post.author.display_name}
        </p>
        <p className="text-xs text-ink/75">
          @{post.author.username} · {time}
          {post.updated_at !== post.created_at ? " · edited" : ""}
        </p>
      </div>
      {showMenu ? (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <IconButton aria-label="Post options" variant="ghost" size="sm">
              <MoreHorizontal className="size-5" aria-hidden="true" />
            </IconButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {isAuthor && onEdit ? (
              <DropdownMenuItem onSelect={onEdit}>Edit</DropdownMenuItem>
            ) : null}
            {onDelete ? (
              <DropdownMenuItem variant="destructive" onSelect={onDelete}>
                Delete
              </DropdownMenuItem>
            ) : null}
          </DropdownMenuContent>
        </DropdownMenu>
      ) : null}
    </div>
  );
}

export default PostHeader;
