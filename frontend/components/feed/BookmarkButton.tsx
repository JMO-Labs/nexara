"use client";
/**
 * @file components/feed/BookmarkButton.tsx
 * @brief Optimistic bookmark toggle for post cards.
 */
import * as React from "react";
import { Bookmark } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { IconButton } from "@/components/ui";
import { useToasts } from "@/stores/toasts";
import { toggleBookmark } from "@/lib/api/bookmarks";

export interface BookmarkButtonProps {
  postId: string;
  isBookmarked: boolean;
}

/**
 * @brief Bookmark toggle; flips immediately, reverts on error.
 * @param postId post id
 * @param isBookmarked initial state
 * @return icon button
 */
export function BookmarkButton({ postId, isBookmarked }: BookmarkButtonProps) {
  const qc = useQueryClient();
  const push = useToasts((s) => s.push);
  const [on, setOn] = React.useState(isBookmarked);
  React.useEffect(() => setOn(isBookmarked), [isBookmarked]);

  const mut = useMutation({
    mutationFn: () => toggleBookmark(postId),
    onMutate: () => setOn((v) => !v),
    onSuccess: (res) => {
      setOn(res.is_bookmarked);
      push({
        variant: "success",
        message: res.is_bookmarked ? "Post bookmarked" : "Bookmark removed",
      });
      qc.invalidateQueries({ queryKey: ["bookmarks"] });
    },
    onError: () => {
      setOn((v) => !v);
      push({ variant: "danger", message: "Could not update bookmark" });
    },
  });

  return (
    <IconButton
      aria-label={on ? "Remove bookmark" : "Bookmark post"}
      aria-pressed={on}
      size="sm"
      variant="ghost"
      onClick={() => mut.mutate()}
    >
      <Bookmark
        className="size-[18px]"
        fill={on ? "currentColor" : "none"}
        aria-hidden="true"
      />
    </IconButton>
  );
}

export default BookmarkButton;
