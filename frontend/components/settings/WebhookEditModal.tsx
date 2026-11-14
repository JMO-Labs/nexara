"use client";
/**
 * @file components/settings/WebhookEditModal.tsx
 * @brief Create/edit webhook dialog; shows the signing secret once on create.
 */
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button, Checkbox, Input, Modal, Switch } from "@/components/ui";
import { useNotificationRegistry } from "@/lib/notifications/registry";
import type {
  WebhookCreateResponse,
  WebhookListItem,
} from "@/lib/notifications/types";

export interface WebhookForm {
  url: string;
  type_keys: string[];
  enabled: boolean;
}

export interface WebhookEditModalProps {
  webhook?: WebhookListItem;
  /** Resolves with the create response (carrying the secret) for new hooks. */
  onSave: (form: WebhookForm) => Promise<WebhookCreateResponse | void>;
  onClose: () => void;
}

/**
 * @brief Webhook form dialog.
 * @param props webhook (edit) or undefined (create), onSave, onClose
 * @return modal
 */
export function WebhookEditModal({
  webhook,
  onSave,
  onClose,
}: WebhookEditModalProps) {
  const t = useTranslations("settings.notif");
  const tr = useTranslations();
  const { types } = useNotificationRegistry();
  const [url, setUrl] = useState(webhook?.url ?? "");
  const [keys, setKeys] = useState<string[]>(webhook?.type_keys ?? []);
  const [enabled, setEnabled] = useState(webhook?.enabled ?? true);
  const [secret, setSecret] = useState<string | null>(null);
  const [error, setError] = useState(false);

  const save = async () => {
    setError(false);
    try {
      const res = await onSave({ url, type_keys: keys, enabled });
      if (res && "secret" in res) setSecret(res.secret);
      else onClose();
    } catch {
      setError(true);
    }
  };
  const toggleKey = (k: string, on: boolean) =>
    setKeys((cur) => (on ? [...cur, k] : cur.filter((x) => x !== k)));

  if (secret) {
    return (
      <Modal
        open
        onClose={onClose}
        title={t("webhook_add")}
        footer={<Button onClick={onClose}>{t("webhook_done")}</Button>}
      >
        <p className="text-sm">{t("webhook_secret")}</p>
        <code className="mt-2 block break-all rounded-lg bg-surface p-2">
          {secret}
        </code>
        <Button
          className="mt-2"
          variant="outline"
          size="sm"
          onClick={() => navigator.clipboard?.writeText(secret)}
        >
          {t("webhook_copy")}
        </Button>
      </Modal>
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={webhook ? t("webhook_edit") : t("webhook_add")}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t("webhook_cancel")}
          </Button>
          <Button onClick={save} disabled={!url}>
            {t("webhook_save")}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Input
          label={t("webhook_url")}
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          error={error ? t("webhook_error") : undefined}
        />
        <fieldset className="space-y-1">
          <legend className="text-sm font-medium">{t("webhook_types")}</legend>
          {types.map((d) => (
            <label
              key={d.key}
              className="flex min-h-9 items-center gap-2 text-sm"
            >
              <Checkbox
                aria-label={tr(d.label_i18n)}
                checked={keys.includes(d.key)}
                onCheckedChange={(v) => toggleKey(d.key, v === true)}
              />
              {tr(d.label_i18n)}
            </label>
          ))}
        </fieldset>
        <label className="flex items-center gap-2 text-sm">
          <Switch
            aria-label={t("webhook_enabled")}
            checked={enabled}
            onCheckedChange={setEnabled}
          />
          {t("webhook_enabled")}
        </label>
      </div>
    </Modal>
  );
}
