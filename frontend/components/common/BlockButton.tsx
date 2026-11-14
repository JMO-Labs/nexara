"use client";
/**
 * @file components/common/BlockButton.tsx
 * @brief Block-user button with confirm dialog.
 */
import * as React from "react";
import { Ban } from "lucide-react";
import { Button } from "@/components/ui";
import { blockUser } from "@/lib/api/moderation";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useToasts } from "@/stores/toasts";

export interface BlockButtonProps {
  userId: string;
  displayName: string;
  size?: "sm" | "md";
}

/**
 * @brief Confirm-then-block button.
 * @param userId user to block
 * @param displayName shown in label and confirm text
 * @return button
 */
export function BlockButton({
  userId,
  displayName,
  size = "sm",
}: BlockButtonProps) {
  const push = useToasts((s) => s.push);
  const [busy, setBusy] = React.useState(false);

  const onClick = async () => {
    const ok = await useConfirmDialog.getState().confirm({
      title: `Block ${displayName}?`,
      message:
        "You will no longer see their content. You can unblock them later in settings.",
      confirmLabel: "Block",
      tone: "danger",
    });
    if (!ok) return;
    setBusy(true);
    try {
      await blockUser(userId);
      push({ variant: "success", message: `${displayName} blocked.` });
    } catch {
      push({ variant: "danger", message: "Couldn't block this user." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Button
      variant="outline"
      size={size}
      onClick={onClick}
      loading={busy}
      aria-label={`Block ${displayName}`}
    >
      <Ban className="size-4" aria-hidden="true" />
      Block
    </Button>
  );
}

export default BlockButton;
