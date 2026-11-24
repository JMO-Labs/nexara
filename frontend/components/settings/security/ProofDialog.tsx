"use client";
/**
 * @file components/settings/security/ProofDialog.tsx
 * @brief Small dialog that asks for a code (or password) to authorise a
 *        sensitive 2FA change.
 */
import { useState, type FormEvent } from "react";
import { Button, Input, Modal } from "@/components/ui";
import { formatApiError } from "@/lib/api/errors";

export interface ProofDialogProps {
  open: boolean;
  title: string;
  label: string;
  confirmLabel: string;
  type?: "text" | "password";
  onClose: () => void;
  onSubmit: (value: string) => Promise<void>;
}

/**
 * @brief Prompt for proof, run the action, close on success.
 * @param props see ProofDialogProps
 * @return modal
 */
export function ProofDialog(p: ProofDialogProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const close = () => {
    setValue("");
    setError(null);
    p.onClose();
  };
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await p.onSubmit(value.trim());
      close();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal open={p.open} onClose={close} title={p.title} size="sm">
      <form onSubmit={submit} className="flex flex-col gap-3">
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Input
          label={p.label}
          type={p.type ?? "text"}
          autoComplete={
            p.type === "password" ? "current-password" : "one-time-code"
          }
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <Button type="submit" loading={busy} disabled={!value.trim()}>
          {p.confirmLabel}
        </Button>
      </form>
    </Modal>
  );
}
