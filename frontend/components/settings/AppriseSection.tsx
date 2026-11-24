"use client";
/**
 * @file components/settings/AppriseSection.tsx
 * @brief "Other apps" settings: list, test, remove and add Apprise URLs.
 */
import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Eye, EyeOff, Send, Trash2 } from "lucide-react";
import { Button, IconButton, Input } from "@/components/ui";
import {
  createAppriseUrl,
  deleteAppriseUrl,
  testAppriseUrl,
  updateAppriseUrl,
} from "@/lib/api/apprise";
import { ApiError } from "@/lib/api/errors";
import { APPRISE_KEY, useAppriseUrls } from "@/hooks/useAppriseUrls";

const INFO_MS = 5000;
const HINT_ID = "apprise-url-hint";
const ERR_ID = "apprise-url-error";

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

  const addError = (e: unknown) => {
    if (e instanceof ApiError) {
      if (e.code === "apprise_url_blocked") return t("apprise_blocked");
      if (e.status === 400 || e.status === 422) return t("apprise_invalid");
    }
    return t("apprise_add_fail");
  };

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
    onError: (e) => setError(addError(e)),
  });
  const resume = useMutation({
    mutationFn: (id: string) => updateAppriseUrl(id, { enabled: true }),
    onMutate: () => setInfo(null),
    onSuccess: refresh,
    onError: () => setInfo(t("apprise_resume_fail")),
  });
  const remove = useMutation({
    mutationFn: deleteAppriseUrl,
    onMutate: () => setInfo(null),
    onSuccess: refresh,
    onError: () => setInfo(t("apprise_remove_fail")),
  });
  const test = useMutation({
    mutationFn: testAppriseUrl,
    onMutate: () => setInfo(null),
    onSuccess: (r) =>
      setInfo(r.status === "sent" ? t("apprise_test_ok") : r.message),
    onError: (e) =>
      setInfo(
        e instanceof ApiError && e.code === "apprise_url_blocked"
          ? t("apprise_blocked")
          : t("apprise_test_fail"),
      ),
  });

  useEffect(() => {
    if (!info) return;
    const id = setTimeout(() => setInfo(null), INFO_MS);
    return () => clearTimeout(id);
  }, [info]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setInfo(null);
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
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{name}</p>
                {a.scheme && (
                  <p className="truncate text-xs text-muted">{a.scheme}://…</p>
                )}
              </div>
              {!a.enabled && (
                <>
                  <span className="rounded-full bg-[color-mix(in_srgb,var(--nx-ink)_10%,transparent)] px-2 py-0.5 text-xs">
                    {t("apprise_paused")}
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    aria-label={`${t("apprise_resume")} ${name}`}
                    disabled={resume.isPending}
                    onClick={() => resume.mutate(a.id)}
                  >
                    {t("apprise_resume")}
                  </Button>
                </>
              )}
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
        <div className="flex flex-col gap-1.5">
          <label htmlFor="apprise-url" className="text-sm font-medium">
            {t("apprise_url")}
          </label>
          <div className="flex items-center gap-2">
            <div className="min-w-0 flex-1">
              <Input
                id="apprise-url"
                type={show ? "text" : "password"}
                autoComplete="off"
                value={url}
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? `${ERR_ID} ${HINT_ID}` : HINT_ID}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>
            <IconButton
              type="button"
              aria-label={show ? t("apprise_hide") : t("apprise_show")}
              onClick={() => setShow((s) => !s)}
            >
              {show ? (
                <EyeOff className="size-4" />
              ) : (
                <Eye className="size-4" />
              )}
            </IconButton>
          </div>
          {error && (
            <p id={ERR_ID} className="text-sm text-destructive">
              {error}
            </p>
          )}
          <p id={HINT_ID} className="text-sm text-muted">
            {t("apprise_hint")}
          </p>
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
