"use client";
/**
 * @file components/settings/AppriseList.tsx
 * @brief List of the user's Apprise URLs with toggle/test/edit/delete.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  Bell,
  Globe,
  Loader2,
  Mail,
  MessageCircle,
  Pencil,
  Send,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { Button, IconButton, Modal, Switch } from "@/components/ui";
import {
  createAppriseUrl,
  deleteAppriseUrl,
  listAppriseUrls,
  testAppriseUrl,
  updateAppriseUrl,
  type AppriseUrl,
} from "@/lib/api/apprise";
import { useToasts } from "@/stores/toasts";
import { AppriseEditModal, type AppriseSubmit } from "./AppriseEditModal";

/** Apprise URL scheme -> icon; Bell is the fallback. */
const SERVICE_ICONS: Record<string, LucideIcon> = {
  slack: MessageCircle,
  discord: MessageCircle,
  tgram: Send,
  mailto: Mail,
  mailtos: Mail,
  ntfy: Bell,
  json: Globe,
  jsons: Globe,
};

export const APPRISE_KEY = ["settings", "apprise"] as const;

/**
 * @brief Query hook for the Apprise URL list.
 * @return TanStack query result
 */
export const useAppriseUrls = () =>
  useQuery({ queryKey: APPRISE_KEY, queryFn: listAppriseUrls });

/**
 * @brief Apprise URL management list.
 * @return list with add/edit/delete/test actions
 */
export function AppriseList() {
  const t = useTranslations("settings.apprise");
  const qc = useQueryClient();
  const { data: items = [] } = useAppriseUrls();
  const [editing, setEditing] = useState<AppriseUrl | "new" | null>(null);
  const [deleting, setDeleting] = useState<AppriseUrl | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: APPRISE_KEY });
  const toast = (variant: "success" | "danger", message: string) =>
    useToasts.getState().push({ variant, message });

  const runTest = async (id: string) => {
    setTestingId(id);
    try {
      const r = await testAppriseUrl(id);
      toast(r.status === "ok" ? "success" : "danger", r.message);
    } catch {
      toast("danger", t("test_failed"));
    } finally {
      setTestingId(null);
    }
  };

  const toggle = useMutation({
    mutationFn: (v: { id: string; enabled: boolean }) =>
      updateAppriseUrl(v.id, { enabled: v.enabled }),
    onSuccess: refresh,
    onError: () => toast("danger", t("action_failed")),
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteAppriseUrl(id),
    onSuccess: () => {
      setDeleting(null);
      return refresh();
    },
    onError: () => toast("danger", t("action_failed")),
  });

  const save = async (v: AppriseSubmit) => {
    const { test, ...body } = v;
    if (editing && editing !== "new") {
      await updateAppriseUrl(editing.id, body);
    } else {
      const created = await createAppriseUrl({ ...body, url: body.url ?? "" });
      if (test) await runTest(created.id);
    }
    await refresh();
  };

  return (
    <div className="space-y-3">
      {items.length === 0 ? (
        <p className="text-sm text-muted">{t("empty")}</p>
      ) : (
        <ul className="divide-y divide-current/10">
          {items.map((it) => {
            const Icon = SERVICE_ICONS[it.service ?? ""] ?? Bell;
            return (
              <li
                key={it.id}
                className="flex flex-wrap items-center gap-3 py-2"
              >
                <Icon
                  aria-hidden
                  data-service={it.service ?? "generic"}
                  className="size-5 shrink-0"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{it.label}</p>
                  {it.service && (
                    <p className="text-xs text-muted">{it.service}</p>
                  )}
                </div>
                <Switch
                  aria-label={`${t("enable")} ${it.label}`}
                  checked={it.enabled}
                  onCheckedChange={(enabled) =>
                    toggle.mutate({ id: it.id, enabled })
                  }
                />
                <IconButton
                  variant="ghost"
                  aria-label={`${t("test")} ${it.label}`}
                  disabled={testingId === it.id}
                  onClick={() => void runTest(it.id)}
                >
                  {testingId === it.id ? (
                    <Loader2 aria-hidden className="size-4 animate-spin" />
                  ) : (
                    <Send aria-hidden className="size-4" />
                  )}
                </IconButton>
                <IconButton
                  variant="ghost"
                  aria-label={`${t("edit")} ${it.label}`}
                  onClick={() => setEditing(it)}
                >
                  <Pencil aria-hidden className="size-4" />
                </IconButton>
                <IconButton
                  variant="ghost"
                  aria-label={`${t("delete")} ${it.label}`}
                  onClick={() => setDeleting(it)}
                >
                  <Trash2 aria-hidden className="size-4" />
                </IconButton>
              </li>
            );
          })}
        </ul>
      )}
      <Button variant="outline" onClick={() => setEditing("new")}>
        {t("add")}
      </Button>

      {editing && (
        <AppriseEditModal
          item={editing === "new" ? undefined : editing}
          onClose={() => setEditing(null)}
          onSave={save}
        />
      )}
      <Modal
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        title={t("delete_title")}
        description={t("delete_msg")}
        size="sm"
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleting(null)}>
              {t("cancel")}
            </Button>
            <Button
              variant="destructive"
              loading={remove.isPending}
              onClick={() => deleting && remove.mutate(deleting.id)}
            >
              {t("delete")}
            </Button>
          </>
        }
      >
        <p className="text-sm">{deleting?.label}</p>
      </Modal>
    </div>
  );
}
