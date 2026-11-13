"use client";
/**
 * @file components/settings/WebhookList.tsx
 * @brief User webhook list with enable toggle, edit, delete and create.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Pencil, Trash2 } from "lucide-react";
import { Button, IconButton, Switch } from "@/components/ui";
import {
  createWebhook,
  deleteWebhook,
  listWebhooks,
  updateWebhook,
} from "@/lib/api/webhooks";
import type { WebhookListItem } from "@/lib/notifications/types";
import { WebhookEditModal, type WebhookForm } from "./WebhookEditModal";

const KEY = ["notifications", "webhooks"] as const;

/**
 * @brief Webhook management list.
 * @return list with create/edit/delete
 */
export function WebhookList() {
  const t = useTranslations("settings.notif");
  const qc = useQueryClient();
  const { data: items = [] } = useQuery({
    queryKey: KEY,
    queryFn: listWebhooks,
  });
  const [editing, setEditing] = useState<WebhookListItem | "new" | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: KEY });
  const toggle = useMutation({
    mutationFn: (w: WebhookListItem) =>
      updateWebhook(w.id, { enabled: !w.enabled }),
    onSuccess: refresh,
  });
  const remove = useMutation({ mutationFn: deleteWebhook, onSuccess: refresh });

  const save = async (form: WebhookForm) => {
    if (editing && editing !== "new") {
      await updateWebhook(editing.id, form);
      await refresh();
      return;
    }
    const res = await createWebhook({
      url: form.url,
      type_keys: form.type_keys,
    });
    await refresh();
    return res;
  };

  return (
    <div className="space-y-3">
      {items.length === 0 && (
        <p className="text-sm text-muted">{t("webhook_empty")}</p>
      )}
      <ul className="space-y-2">
        {items.map((w) => (
          <li key={w.id} className="flex flex-wrap items-center gap-2">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{w.url}</p>
              <p className="truncate text-xs text-muted">
                {w.type_keys.join(", ")}
              </p>
            </div>
            <Switch
              aria-label={`${t("webhook_enabled")} ${w.url}`}
              checked={w.enabled}
              onCheckedChange={() => toggle.mutate(w)}
            />
            <IconButton
              aria-label={`${t("webhook_edit")} ${w.url}`}
              onClick={() => setEditing(w)}
            >
              <Pencil className="size-4" />
            </IconButton>
            <IconButton
              aria-label={`${t("webhook_delete")} ${w.url}`}
              onClick={() => remove.mutate(w.id)}
            >
              <Trash2 className="size-4" />
            </IconButton>
          </li>
        ))}
      </ul>
      <Button size="sm" onClick={() => setEditing("new")}>
        {t("webhook_add")}
      </Button>
      {editing && (
        <WebhookEditModal
          webhook={editing === "new" ? undefined : editing}
          onSave={save}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}
