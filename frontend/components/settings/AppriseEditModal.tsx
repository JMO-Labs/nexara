"use client";
/**
 * @file components/settings/AppriseEditModal.tsx
 * @brief Add/edit form for an Apprise URL.
 */
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button, Input, Modal, Switch, Textarea } from "@/components/ui";
import { serviceFromUrl, type AppriseUrl } from "@/lib/api/apprise";

export interface AppriseSubmit {
  url?: string;
  label: string;
  enabled: boolean;
  /** True when the user chose "Save and test". */
  test?: boolean;
}

export interface AppriseEditModalProps {
  /** Existing entry when editing; undefined when creating. */
  item?: AppriseUrl;
  onClose: () => void;
  onSave: (v: AppriseSubmit) => Promise<void>;
}

/**
 * @brief Modal form; on create offers a "Save and test?" step.
 * @param props see AppriseEditModalProps
 * @return modal element
 */
export function AppriseEditModal({
  item,
  onClose,
  onSave,
}: AppriseEditModalProps) {
  const t = useTranslations("settings.apprise");
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState(item?.label ?? "");
  const [enabled, setEnabled] = useState(item?.enabled ?? true);
  const [error, setError] = useState<string>();
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  const service = serviceFromUrl(url);
  const validate = () => {
    if (!item || url) {
      if (!service) {
        setError(t("invalid_url"));
        return false;
      }
    }
    setError(undefined);
    return true;
  };

  const submit = async (test: boolean) => {
    setBusy(true);
    try {
      await onSave({
        url: url.trim() || undefined,
        label: label.trim(),
        enabled,
        test,
      });
      onClose();
    } catch {
      setConfirm(false);
      setError(t("save_failed"));
    } finally {
      setBusy(false);
    }
  };

  const onSaveClick = () => {
    if (!validate()) return;
    if (item) void submit(false);
    else setConfirm(true);
  };

  if (confirm) {
    return (
      <Modal
        open
        onClose={onClose}
        title={t("save_and_test")}
        description={t("save_and_test_msg")}
        size="sm"
        footer={
          <>
            <Button
              variant="outline"
              loading={busy}
              onClick={() => void submit(false)}
            >
              {t("no")}
            </Button>
            <Button
              variant="secondary"
              loading={busy}
              onClick={() => void submit(true)}
            >
              {t("yes")}
            </Button>
          </>
        }
      >
        <p className="text-sm">{label}</p>
      </Modal>
    );
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={item ? t("edit") : t("add")}
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            {t("cancel")}
          </Button>
          <Button variant="secondary" onClick={onSaveClick}>
            {t("save")}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Textarea
          label={t("url")}
          rows={3}
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={item ? "••••••••" : "slack://tokenA/tokenB/tokenC"}
          hint={service ? `${service}` : t("url_hint")}
          error={error}
          autoComplete="off"
          spellCheck={false}
        />
        <Input
          label={t("label")}
          value={label}
          onChange={(e) => setLabel(e.target.value)}
        />
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <Switch
            aria-label={t("enable")}
            checked={enabled}
            onCheckedChange={setEnabled}
          />
          {t("enable")}
        </label>
      </div>
    </Modal>
  );
}
