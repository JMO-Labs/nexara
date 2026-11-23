"use client";
/**
 * @file components/feed/ComposerToolbar.tsx
 * @brief Action row for PostComposer: photos, poll, kudos, cancel, post.
 */
import {
  Image as ImageIcon,
  BarChart3,
  Hourglass,
  Mic,
  PartyPopper,
  Trophy,
  X,
} from "lucide-react";
import { Button, IconButton } from "@/components/ui";

export interface ComposerToolbarProps {
  posting: boolean;
  onSubmit: () => void;
  onCancel: () => void;
  onKudos?: () => void;
  onCelebrate?: () => void;
  onCapsule?: () => void;
  onRecord?: () => void;
  onPhotos?: () => void;
  onPoll?: () => void;
  postDisabled?: boolean;
}

/**
 * @brief Photo, poll and kudos icon buttons (each hidden without a handler).
 * @param onKudos opens the kudos composer
 * @param onPhotos opens the file picker
 * @param onPoll toggles the poll editor
 * @return fragment of icon buttons
 */
export function ComposerIcons({
  onKudos,
  onCelebrate,
  onCapsule,
  onRecord,
  onPhotos,
  onPoll,
}: {
  onKudos?: () => void;
  onCelebrate?: () => void;
  onCapsule?: () => void;
  onRecord?: () => void;
  onPhotos?: () => void;
  onPoll?: () => void;
}) {
  return (
    <>
      <IconButton
        aria-label="Add photos"
        variant="ghost"
        size="sm"
        onClick={onPhotos}
        disabled={!onPhotos}
      >
        <ImageIcon className="size-[18px]" aria-hidden />
      </IconButton>
      <IconButton
        aria-label="Add poll"
        variant="ghost"
        size="sm"
        onClick={onPoll}
        disabled={!onPoll}
      >
        <BarChart3 className="size-[18px]" aria-hidden />
      </IconButton>
      {onRecord ? (
        <IconButton
          aria-label="Record a voice note"
          variant="ghost"
          size="sm"
          onClick={onRecord}
        >
          <Mic className="size-[18px]" aria-hidden />
        </IconButton>
      ) : null}
      {onCelebrate ? (
        <IconButton
          aria-label="Celebrate someone"
          variant="ghost"
          size="sm"
          onClick={onCelebrate}
        >
          <PartyPopper className="size-[18px]" aria-hidden />
        </IconButton>
      ) : null}
      {onCapsule ? (
        <IconButton
          aria-label="Seal a time capsule"
          variant="ghost"
          size="sm"
          onClick={onCapsule}
        >
          <Hourglass className="size-[18px]" aria-hidden />
        </IconButton>
      ) : null}
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
  onCelebrate,
  onCapsule,
  onRecord,
  onPhotos,
  onPoll,
  postDisabled,
}: ComposerToolbarProps) {
  return (
    <div className="mt-2 flex items-center gap-2">
      <ComposerIcons
        onKudos={onKudos}
        onCelebrate={onCelebrate}
        onCapsule={onCapsule}
        onRecord={onRecord}
        onPhotos={onPhotos}
        onPoll={onPoll}
      />
      <div className="grow" />
      <IconButton
        aria-label="Cancel"
        variant="ghost"
        size="sm"
        onClick={onCancel}
      >
        <X className="size-[18px]" aria-hidden />
      </IconButton>
      <Button
        onClick={onSubmit}
        loading={posting}
        disabled={postDisabled}
        size="sm"
      >
        Post
      </Button>
    </div>
  );
}

export default ComposerToolbar;
