"use client";
/**
 * @file components/admin/plugins/CredentialsDialog.tsx
 * @brief One-time display of a plugin's token and webhook secret.
 */
import { Copy } from "lucide-react";
import { Button, IconButton, Modal } from "@/components/ui";
import { useToasts } from "@/stores/toasts";
import type { PluginCredentials } from "@/lib/api/plugins";

/**
 * @brief Credentials dialog; the secrets only exist in memory while open.
 * @param credentials secrets from the first enable, or null
 * @param onClose close handler (drops the secrets)
 * @return modal
 */
export function CredentialsDialog({
  credentials,
  onClose,
}: {
  credentials: PluginCredentials | null;
  onClose: () => void;
}) {
  const push = useToasts((s) => s.push);
  const copy = async (label: string, v: string) => {
    try {
      await navigator.clipboard.writeText(v);
      push({ variant: "success", message: `${label} copied` });
    } catch {
      push({ variant: "danger", message: "Copy failed" });
    }
  };
  const rows = credentials
    ? [
        ["Token", credentials.token],
        ["Webhook secret", credentials.webhook_secret],
      ]
    : [];
  return (
    <Modal
      open={credentials !== null}
      onClose={onClose}
      title="Plugin credentials"
      description="Copy these now. They will not be shown again."
      footer={<Button onClick={onClose}>Done</Button>}
    >
      <div className="flex flex-col gap-3">
        {rows.map(([label, value]) => (
          <div key={label} className="flex flex-col gap-1">
            <span className="text-sm font-medium">{label}</span>
            <div className="flex items-center gap-2">
              <code className="min-w-0 flex-1 break-all rounded-lg bg-surface p-2 text-xs">
                {value}
              </code>
              <IconButton
                aria-label={`Copy ${label.toLowerCase()}`}
                onClick={() => copy(label, value)}
              >
                <Copy className="size-4" />
              </IconButton>
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}
