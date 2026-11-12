"use client";
/**
 * @file components/feed/ReactionRow.tsx
 * @brief Reaction chips + add-reaction picker + comment count.
 */
import * as React from "react";
import { MessageCircle, Smile } from "lucide-react";
import { IconButton } from "@/components/ui";
import type { ReactionSummary } from "@/lib/api/posts";

const QUICK = ["👍", "❤️", "😂", "🎉", "😮", "🙏"];

export interface ReactionRowProps {
  reactions: ReactionSummary[];
  commentCount: number;
  onReact: (emoji: string) => void;
  onCommentClick?: () => void;
  extra?: React.ReactNode;
}

/**
 * @brief Row of reaction toggles with a quick-pick popover.
 * @param reactions summary per emoji
 * @param commentCount number of comments
 * @param onReact toggle handler
 * @param onCommentClick toggles the comment thread
 * @return row element
 */
export function ReactionRow({
  reactions,
  commentCount,
  onReact,
  onCommentClick,
  extra,
}: ReactionRowProps) {
  const [open, setOpen] = React.useState(false);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {reactions.map((r) => (
        <button
          key={r.emoji}
          type="button"
          aria-pressed={r.reacted_by_me}
          aria-label={`${r.emoji} reaction, ${r.count} ${r.count === 1 ? "person" : "people"}`}
          onClick={() => onReact(r.emoji)}
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm text-ink outline-none transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
            r.reacted_by_me
              ? "border-accent bg-accent/15"
              : "border-ink/20 bg-bg hover:bg-ink/5"
          }`}
        >
          {r.emoji} {r.count}
        </button>
      ))}
      <div
        className="relative"
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
      >
        <IconButton
          aria-label="Add reaction"
          aria-expanded={open}
          size="sm"
          variant="ghost"
          onClick={() => setOpen((v) => !v)}
        >
          <Smile className="size-[18px]" aria-hidden="true" />
        </IconButton>
        {open ? (
          <div
            role="group"
            aria-label="Pick a reaction"
            className="absolute bottom-full left-0 z-10 mb-1 flex gap-1 rounded-xl bg-surface p-1 shadow-md"
          >
            {QUICK.map((e) => (
              <IconButton
                key={e}
                aria-label={`React ${e}`}
                size="sm"
                variant="ghost"
                onClick={() => {
                  onReact(e);
                  setOpen(false);
                }}
              >
                <span className="text-lg">{e}</span>
              </IconButton>
            ))}
          </div>
        ) : null}
      </div>
      <div className="grow" />
      {extra}
      <IconButton
        aria-label="Comments"
        size="sm"
        variant="ghost"
        onClick={onCommentClick}
      >
        <MessageCircle className="size-[18px]" aria-hidden="true" />
      </IconButton>
      <span className="text-xs text-ink/75">{commentCount}</span>
    </div>
  );
}

export default ReactionRow;
