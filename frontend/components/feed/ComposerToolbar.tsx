"use client";
/**
 * @file components/feed/ComposerToolbar.tsx
 * @brief Action row for PostComposer: disabled attach/poll, cancel, post.
 */
import { Image as ImageIcon, BarChart3, X } from "lucide-react";
import { Button, IconButton } from "@/components/ui";

export interface ComposerToolbarProps {
  posting: boolean;
  onSubmit: () => void;
  onCancel: () => void;
}

/**
 * @brief Composer action row.
 * @param posting submit in flight
 * @param onSubmit post handler
 * @param onCancel cancel handler
 * @return toolbar element
 */
export function ComposerToolbar({
  posting,
  onSubmit,
  onCancel,
}: ComposerToolbarProps) {
  return (
    <div className="mt-2 flex items-center gap-2">
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
