"use client";
/**
 * @file components/settings/AppriseSection.tsx
 * @brief "Other apps" settings: list, test, remove and add Apprise URLs.
 */
import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Eye, EyeOff, Send, Trash2 } from "lucide-react";
import { Button, IconButton, Input } from "@/components/ui";
import {
  createAppriseUrl,
  deleteAppriseUrl,
  testAppriseUrl,
} from "@/lib/api/apprise";
import { ApiError } from "@/lib/api/errors";
import { APPRISE_KEY, useAppriseUrls } from "@/hooks/useAppriseUrls";

/**
 * @brief Apprise apps manager.
 * @return list plus add form
 */
export function AppriseSection() {
  const t = useTranslations("settings.notif");
  const qc = useQueryClient();
  const { data: items = [] } = useAppriseUrls();
  const [label, setLabel] = useState("");
  const [url, setUrl] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: APPRISE_KEY });

  const add = useMutation({
    mutationFn: () =>
      createAppriseUrl({
        apprise_url: url.trim(),
        ...(label.trim() ? { label: label.trim() } : {}),
      }),
    onSuccess: () => {
      setLabel("");
      setUrl("");
      setError(null);
      return refresh();
    },
    onError: (e) =>
      setError(
        e instanceof ApiError && e.code === "apprise_url_blocked"
          ? t("apprise_blocked")
          : t("apprise_invalid"),
      ),
  });
  const remove = useMutation({
    mutationFn: deleteAppriseUrl,
    onSuccess: refresh,
  });
  const test = useMutation({
    mutationFn: testAppriseUrl,
    onSuccess: (r) =>
      setInfo(r.status === "sent" ? t("apprise_test_ok") : r.message),
    onError: () => setInfo(t("apprise_test_fail")),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (url.trim()) add.mutate();
  };

  return (
    <div className="space-y-3">
      {items.length === 0 && (
        <p className="text-sm text-muted">{t("apprise_empty")}</p>
      )}
      <ul className="space-y-2">
        {items.map((a) => {
          const name = a.label || t("apprise_unnamed");
          return (
            <li key={a.id} className="flex items-center gap-2">
              <p className="min-w-0 flex-1 truncate text-sm font-medium">
                {name}
              </p>
              <IconButton
                aria-label={`${t("apprise_test")} ${name}`}
                onClick={() => test.mutate(a.id)}
              >
                <Send className="size-4" />
              </IconButton>
              <IconButton
                aria-label={`${t("apprise_remove")} ${name}`}
                onClick={() => remove.mutate(a.id)}
              >
                <Trash2 className="size-4" />
              </IconButton>
            </li>
          );
        })}
      </ul>
      <p role="status" className="text-xs text-muted">
        {info}
      </p>
      <form onSubmit={submit} className="space-y-2">
        <Input
          label={t("apprise_label")}
          value={label}
          maxLength={100}
          onChange={(e) => setLabel(e.target.value)}
        />
        <div className="flex items-end gap-2">
          <div className="min-w-0 flex-1">
            <Input
              label={t("apprise_url")}
              type={show ? "text" : "password"}
              autoComplete="off"
              value={url}
              error={error ?? undefined}
              hint={t("apprise_hint")}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
          <IconButton
            type="button"
            aria-label={show ? t("apprise_hide") : t("apprise_show")}
            onClick={() => setShow((s) => !s)}
          >
            {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </IconButton>
        </div>
        <div className="flex items-center gap-3">
          <Button
            type="submit"
            size="sm"
            disabled={!url.trim() || add.isPending}
          >
            {t("apprise_add")}
          </Button>
          <a
            href="https://github.com/caronc/apprise/wiki"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm underline"
          >
            {t("apprise_services")}
          </a>
        </div>
      </form>
    </div>
  );
}
