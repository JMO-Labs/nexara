"use client";
/**
 * @file components/admin/prompts-tab/NewPromptModal.tsx
 * @brief Modal form for creating a prompt.
 */
import { useState } from "react";
import {
  Button,
  Input,
  Modal,
  Option,
  Select,
  Textarea,
} from "@/components/ui";
import type { PromptCreate } from "@/lib/api/prompts";
import { FREQUENCIES } from "./constants";

interface Props {
  open: boolean;
  creating: boolean;
  onClose: () => void;
  onCreate: (form: PromptCreate) => void;
}

const EMPTY: PromptCreate = { title: "", body: "", frequency: "annual_date" };

/**
 * @brief Create-prompt dialog.
 * @param props open state and callbacks
 * @return modal
 */
export function NewPromptModal({ open, creating, onClose, onCreate }: Props) {
  const [form, setForm] = useState<PromptCreate>(EMPTY);

  const submit = () => {
    if (!form.title.trim() || !form.body.trim()) return;
    onCreate(form);
    setForm(EMPTY);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create new prompt"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={creating}>
            Create
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Input
          label="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder="Prompt title"
        />
        <Textarea
          label="Body"
          rows={3}
          value={form.body}
          onChange={(e) => setForm({ ...form, body: e.target.value })}
          placeholder="Prompt body"
        />
        <div className="flex flex-col gap-1.5">
          <span className="text-sm font-semibold">Frequency</span>
          <Select
            label="Frequency"
            value={form.frequency}
            onValueChange={(v) => setForm({ ...form, frequency: v })}
          >
            {FREQUENCIES.map((f) => (
              <Option key={f.value} value={f.value}>
                {f.label}
              </Option>
            ))}
          </Select>
        </div>
      </div>
    </Modal>
  );
}
