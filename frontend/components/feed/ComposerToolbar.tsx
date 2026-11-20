"use client";
/**
 * @file components/feed/ComposerToolbar.tsx
 * @brief Action row for PostComposer: attach/poll (disabled), kudos, cancel, post.
 */
import { Image as ImageIcon, BarChart3, Trophy, X } from "lucide-react";
import { Button, IconButton } from "@/components/ui";

export interface ComposerToolbarProps {
  posting: boolean;
  onSubmit: () => void;
  onCancel: () => void;
  onKudos?: () => void;
}

/**
 * @brief Image, poll (disabled) and kudos icon buttons.
 * @param onKudos opens the kudos composer
 * @return fragment of icon buttons
 */
export function ComposerIcons({ onKudos }: { onKudos?: () => void }) {
  return (
    <>
      <IconButton
        aria-label="Attach media"
        variant="ghost"
        size="sm"
        disabled
        title="Coming soon"
      >
        <ImageIcon className="size-[18px]" aria-hidden />
      </IconButton>
      <IconButton
        aria-label="Add poll"
        variant="ghost"
        size="sm"
        disabled
        title="Coming soon"
      >
        <BarChart3 className="size-[18px]" aria-hidden />
      </IconButton>
      {onKudos ? (
        <IconButton
          aria-label="Send kudos"
          variant="ghost"
          size="sm"
          onClick={onKudos}
        >
          <Trophy className="size-[18px]" aria-hidden />
        </IconButton>
      ) : null}
    </>
  );
}

/**
 * @brief Composer action row.
 * @param posting submit in flight
 * @param onSubmit post handler
 * @param onCancel cancel handler
 * @param onKudos optional kudos trigger
 * @return toolbar element
 */
export function ComposerToolbar({
  posting,
  onSubmit,
  onCancel,
  onKudos,
}: ComposerToolbarProps) {
  return (
    <div className="mt-2 flex items-center gap-2">
      <ComposerIcons onKudos={onKudos} />
      <div className="grow" />
      <IconButton
        aria-label="Cancel"
        variant="ghost"
        size="sm"
        onClick={onCancel}
      >
        <X className="size-[18px]" aria-hidden />
      </IconButton>
      <Button onClick={onSubmit} loading={posting} size="sm">
        Post
      </Button>
    </div>
  );
}

export default ComposerToolbar;
