"use client";
/**
 * @file components/settings/security/RecoveryCodes.tsx
 * @brief Shows freshly issued recovery codes once, with copy/download and a
 *        "saved" checkbox that gates closing.
 */
import { useState } from "react";
import { Button, Modal } from "@/components/ui";
import { Checkbox } from "@/components/ui/Checkbox";

export interface RecoveryCodesProps {
  codes: string[] | null;
  onDone: () => void;
}

/**
 * @brief Recovery codes dialog (cannot be dismissed until acknowledged).
 * @param codes codes to show; null closes the dialog
 * @param onDone called after the user confirms they saved the codes
 * @return modal
 */
export function RecoveryCodes({ codes, onDone }: RecoveryCodesProps) {
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  const text = (codes ?? []).join("\n");
  const done = () => {
    setSaved(false);
    setCopied(false);
    onDone();
  };
  const copy = async () => {
    await navigator.clipboard?.writeText(text);
    setCopied(true);
  };
  const download = () => {
    const url = URL.createObjectURL(
      new Blob([text + "\n"], { type: "text/plain" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "nexara-recovery-codes.txt";
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <Modal
      open={codes !== null}
      onClose={() => saved && done()}
      title="Save your recovery codes"
      description="Each code works once if you lose your authenticator. They will not be shown again."
      size="sm"
      footer={
        <Button disabled={!saved} onClick={done}>
          Done
        </Button>
      }
    >
      <ul
        aria-label="Recovery codes"
        className="grid grid-cols-2 gap-2 font-mono text-sm"
      >
        {(codes ?? []).map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2">
        <Button variant="ghost" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </Button>
        <Button variant="ghost" onClick={download}>
          Download .txt
        </Button>
      </div>
      <label className="mt-4 flex min-h-11 items-center gap-2 text-sm">
        <Checkbox
          checked={saved}
          onCheckedChange={(v) => setSaved(v === true)}
        />
        I saved these
      </label>
    </Modal>
  );
}
