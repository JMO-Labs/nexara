"use client";
/**
 * @file components/expenses/ExpenseForm.tsx
 * @brief Add an expense: amount (decimal input), who paid, equal or custom split.
 */
import { useState } from "react";
import { Button, Input } from "@/components/ui";
import { Segmented } from "@/components/ui/page";
import {
  Field,
  MoneyInput,
  selectCls,
} from "@/components/wishlists/wizard/fields";
import {
  formatCents,
  type ExpenseInput,
  type LedgerMember,
} from "@/lib/api/expenses";
import { MemberPicker } from "./MemberPicker";

/** @brief Today as YYYY-MM-DD in the viewer's timezone. */
export function todayLocal(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/**
 * @brief Expense form.
 * @param members ledger members
 * @param currency ledger currency
 * @param meId signed-in user id (default payer)
 * @param onSubmit receives the API body; reject to show an error
 * @return form
 */
export function ExpenseForm({
  members,
  currency,
  meId,
  onSubmit,
}: {
  members: LedgerMember[];
  currency: string;
  meId: string;
  onSubmit: (b: ExpenseInput) => Promise<void>;
}) {
  const all = members.map((m) => m.user_id);
  const [cents, setCents] = useState<number | null>(null);
  const [desc, setDesc] = useState("");
  const [date, setDate] = useState(todayLocal());
  const [payer, setPayer] = useState(all.includes(meId) ? meId : all[0]);
  const [split, setSplit] = useState<"equal" | "custom">("equal");
  const [among, setAmong] = useState<string[]>(all);
  const [custom, setCustom] = useState<Record<string, number | null>>({});
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  const customSum = Object.values(custom).reduce<number>(
    (a, c) => a + (c ?? 0),
    0,
  );

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cents || cents <= 0) return setError("Enter an amount");
    if (!desc.trim()) return setError("Describe the expense");
    if (split === "equal" && among.length === 0)
      return setError("Pick who is splitting it");
    if (split === "custom" && customSum !== cents)
      return setError(
        `Shares add up to ${formatCents(customSum, currency)}, not ${formatCents(cents, currency)}`,
      );
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit({
        payer_id: payer,
        amount_cents: cents,
        description: desc.trim(),
        spent_on: date,
        split,
        split_among: split === "equal" ? among : null,
        shares:
          split === "custom"
            ? all
                .filter((id) => (custom[id] ?? 0) > 0)
                .map((id) => ({ user_id: id, amount_cents: custom[id] ?? 0 }))
            : null,
      });
      setCents(null);
      setDesc("");
      setCustom({});
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not add the expense",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Amount">
          <MoneyInput
            cents={cents}
            onChange={setCents}
            currency={currency}
            label="Amount"
          />
        </Field>
        <Input
          label="What was it for"
          value={desc}
          maxLength={200}
          onChange={(e) => setDesc(e.target.value)}
        />
        <Input
          label="Date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <Field label="Paid by">
          <select
            className={selectCls}
            value={payer}
            onChange={(e) => setPayer(e.target.value)}
          >
            {members.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Segmented
        label="How to split"
        value={split}
        onChange={setSplit}
        options={[
          { value: "equal", label: "Split equally" },
          { value: "custom", label: "Custom amounts" },
        ]}
      />
      {split === "equal" ? (
        <MemberPicker
          legend="Split between"
          people={members.map((m) => ({ id: m.user_id, display_name: m.name }))}
          value={among}
          onChange={setAmong}
        />
      ) : (
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-medium">
            Each person&apos;s share
          </legend>
          {members.map((m) => (
            <div key={m.user_id} className="flex items-center gap-3">
              <span className="w-32 shrink-0 truncate text-sm">{m.name}</span>
              <MoneyInput
                cents={custom[m.user_id] ?? null}
                onChange={(c) => setCustom((s) => ({ ...s, [m.user_id]: c }))}
                currency={currency}
                label={`Share for ${m.name}`}
              />
            </div>
          ))}
          <p className="text-xs text-muted" aria-live="polite">
            Total {formatCents(customSum, currency)}
            {cents ? ` of ${formatCents(cents, currency)}` : ""}
          </p>
        </fieldset>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <Button type="submit" loading={busy}>
        Add expense
      </Button>
    </form>
  );
}
