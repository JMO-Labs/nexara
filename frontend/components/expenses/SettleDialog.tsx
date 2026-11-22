"use client";
/**
 * @file components/expenses/SettleDialog.tsx
 * @brief Confirm a payment between two members (amount editable, capped).
 */
import { useState } from "react";
import { Button, Modal } from "@/components/ui";
import { MoneyInput } from "@/components/wishlists/wizard/fields";
import { formatCents, type Transfer } from "@/lib/api/expenses";

/**
 * @brief Settle dialog.
 * @param transfer the suggested payment, or null when closed
 * @param currency ledger currency
 * @param onClose close callback
 * @param onConfirm record the payment (cents)
 * @return modal
 */
export function SettleDialog({
  transfer,
  currency,
  onClose,
  onConfirm,
}: {
  transfer: Transfer | null;
  currency: string;
  onClose: () => void;
  onConfirm: (t: Transfer, cents: number) => Promise<void>;
}) {
  const [cents, setCents] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | undefined>();
  if (!transfer) return null;
  const amount = cents ?? transfer.cents;
  const bad = amount <= 0 || amount > transfer.cents;
  const go = async () => {
    setBusy(true);
    setError(undefined);
    try {
      await onConfirm(transfer, amount);
      setCents(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not settle");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal
      open
      onClose={onClose}
      title="Mark as paid"
      description={`${transfer.from_name} paid ${transfer.to_name}`}
      size="sm"
      footer={
        <>
          <Button variant="glass" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={go} loading={busy} disabled={bad}>
            Settle {formatCents(amount, currency)}
          </Button>
        </>
      }
    >
      <MoneyInput
        cents={amount}
        onChange={setCents}
        currency={currency}
        label="Amount paid"
      />
      <p className="mt-1 text-xs text-muted">
        Up to {formatCents(transfer.cents, currency)}.
      </p>
      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
    </Modal>
  );
}
