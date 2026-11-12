"use client";
/**
 * @file components/events/subscriptions/AddModal.tsx
 * @brief Add calendar subscription modal with form.
 */
import * as React from "react";
import { useTranslations } from "next-intl";
import { Button, Input, Modal, Select, Option } from "@/components/ui";
import { INTERVALS } from "./intervals";

export interface AddModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: {
    title: string;
    source_url: string;
    sync_interval_minutes: number;
  }) => void;
  isLoading: boolean;
}

const EMPTY = { title: "", sourceUrl: "", interval: 60 };

/**
 * @param props see AddModalProps
 * @return modal with title/url/interval form
 */
export function AddModal({
  open,
  onClose,
  onSubmit,
  isLoading,
}: AddModalProps) {
  const t = useTranslations();
  const [form, setForm] = React.useState(EMPTY);

  const handleSubmit = () => {
    if (!form.title || !form.sourceUrl) return;
    onSubmit({
      title: form.title,
      source_url: form.sourceUrl,
      sync_interval_minutes: form.interval,
    });
    setForm(EMPTY);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("components.calendar.subscriptions.add_modal_title")}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            {t("actions.cancel")}
          </Button>
          <Button
            onClick={handleSubmit}
            loading={isLoading}
            disabled={!form.title || !form.sourceUrl}
          >
            {t("actions.add")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Input
          label={t("components.calendar.subscriptions.title")}
          placeholder="e.g., Work Calendar"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          disabled={isLoading}
        />
        <Input
          label={t("components.calendar.subscriptions.url")}
          type="url"
          placeholder="https://example.com/calendar.ics"
          value={form.sourceUrl}
          onChange={(e) => setForm({ ...form, sourceUrl: e.target.value })}
          disabled={isLoading}
        />
        <Select
          label={t("components.calendar.subscriptions.interval")}
          value={String(form.interval)}
          onValueChange={(v) => setForm({ ...form, interval: Number(v) })}
          disabled={isLoading}
        >
          {INTERVALS.map(([m, , long]) => (
            <Option key={m} value={String(m)}>
              {long}
            </Option>
          ))}
        </Select>
      </div>
    </Modal>
  );
}
