"use client";
/**
 * @file components/admin/ResetTwoFactorButton.tsx
 * @brief Admin row action: confirm, then clear a member's 2FA.
 */
import { useState } from "react";
import { ShieldOff } from "lucide-react";
import { IconButton } from "@/components/ui";
import { useConfirmDialog } from "@/stores/confirmDialog";
import { useToasts } from "@/stores/toasts";
import { formatApiError } from "@/lib/api/errors";
import { resetUserTwoFactor } from "@/lib/api/twoFactor";

/**
 * @brief Reset-2FA icon button with confirm dialog.
 * @param userId target member
 * @param name display name for the confirm text
 * @return button
 */
export function ResetTwoFactorButton({
  userId,
  name,
}: {
  userId: string;
  name: string;
}) {
  const confirm = useConfirmDialog((s) => s.confirm);
  const push = useToasts((s) => s.push);
  const [busy, setBusy] = useState(false);
  const onClick = async () => {
    const ok = await confirm({
      title: "Reset 2FA?",
      message: `${name} will lose their authenticator, recovery codes and passkeys.`,
      confirmLabel: "Reset 2FA",
      tone: "danger",
    });
    if (!ok) return;
    setBusy(true);
    try {
      await resetUserTwoFactor(userId);
      push({ variant: "success", message: "2FA reset" });
    } catch (e) {
      push({ variant: "danger", message: formatApiError(e) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <IconButton
      variant="glass"
      aria-label="Reset 2FA"
      tooltip="Reset 2FA"
      disabled={busy}
      onClick={onClick}
    >
      <ShieldOff className="size-4" aria-hidden="true" />
    </IconButton>
  );
}
