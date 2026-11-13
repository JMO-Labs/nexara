"use client";
/**
 * @file components/admin/PluginInstallDialog.tsx
 * @brief Two-step install: pick plugin, then review manifest and permissions.
 */
import { useState } from "react";
import { Button, Input, Modal } from "@/components/ui";
import {
  useInstallConfirm,
  useInstallRequest,
  type InstallReview,
} from "@/lib/api/plugins";
import { PluginPermissionList } from "./PluginPermissionList";

export interface PluginInstallDialogProps {
  open: boolean;
  onClose: () => void;
}

/**
 * @brief Install dialog.
 * @param props open state and close handler
 * @return modal
 */
export function PluginInstallDialog({
  open,
  onClose,
}: PluginInstallDialogProps) {
  const [pluginId, setPluginId] = useState("");
  const [review, setReview] = useState<InstallReview | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const id = pluginId.trim();
  const request = useInstallRequest(id);
  const confirm = useInstallConfirm(id);

  const close = () => {
    setPluginId("");
    setReview(null);
    setApiKey(null);
    onClose();
  };

  if (apiKey) {
    return (
      <Modal
        open={open}
        onClose={close}
        title="Plugin installed"
        description="Copy this API key now. It will not be shown again."
        footer={<Button onClick={close}>Done</Button>}
      >
        <code className="block break-all rounded-xl bg-surface p-3 text-sm">
          {apiKey}
        </code>
      </Modal>
    );
  }

  if (review) {
    const m = review.manifest;
    return (
      <Modal
        open={open}
        onClose={close}
        title={`Install ${m.name}`}
        description="Step 2 of 2: review permissions"
        size="lg"
        footer={
          <>
            <Button variant="outline" onClick={close}>
              Cancel
            </Button>
            <Button
              loading={confirm.isPending}
              onClick={() =>
                confirm.mutate(undefined, {
                  onSuccess: (r) => setApiKey(r.api_key),
                })
              }
            >
              Install
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          <p className="text-sm">{m.description}</p>
          <p className="text-xs text-muted">
            v{m.version} by {m.author}
          </p>
          <PluginPermissionList
            permissions={review.permissions_requested}
            newPermissions={review.new_permissions}
          />
        </div>
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Install plugin"
      description="Step 1 of 2: choose a plugin"
      footer={
        <>
          <Button variant="outline" onClick={close}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="plugin-install-form"
            loading={request.isPending}
            disabled={!id}
          >
            Review
          </Button>
        </>
      }
    >
      <form
        id="plugin-install-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (id) request.mutate(undefined, { onSuccess: setReview });
        }}
      >
        <Input
          label="Plugin ID"
          hint="Identifier of a plugin present in the plugins directory"
          value={pluginId}
          onChange={(e) => setPluginId(e.target.value)}
          autoComplete="off"
        />
      </form>
    </Modal>
  );
}

export default PluginInstallDialog;
