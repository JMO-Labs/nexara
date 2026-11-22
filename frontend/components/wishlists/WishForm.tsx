"use client";
/**
 * @file components/wishlists/WishForm.tsx
 * @brief Add or edit one wish: a gift (name, link, price, how many, notes)
 *        or a cash fund (name, goal, notes).
 */
import * as React from "react";
import { Gift, PiggyBank } from "lucide-react";
import { Button, Input } from "@/components/ui";
import { Segmented } from "@/components/ui/page";
import type { Wish, WishInput } from "@/lib/api/wishlists";
import { MoneyInput } from "./wizard/fields";

type Kind = "gift" | "fund";

/**
 * @brief Wish fields.
 * @param wish existing wish to edit, or undefined to add
 * @param currency list currency
 * @param pending saving
 * @param onSave called with the body; resolves to reset the form
 * @param onCancel optional cancel (edit mode)
 * @return form
 */
export function WishForm({
  wish,
  currency,
  pending,
  onSave,
  onCancel,
}: {
  wish?: Wish;
  currency: string;
  pending: boolean;
  onSave: (body: WishInput) => Promise<unknown>;
  onCancel?: () => void;
}) {
  const [kind, setKind] = React.useState<Kind>(wish?.kind ?? "gift");
  const blank = { name: "", url: "", qty: "1", notes: "" };
  const [f, setF] = React.useState(
    wish
      ? {
          name: wish.name,
          url: wish.url ?? "",
          qty: String(wish.qty),
          notes: wish.notes ?? "",
        }
      : blank,
  );
  const [price, setPrice] = React.useState<number | null>(
    wish?.price_cents ?? null,
  );
  const [goal, setGoal] = React.useState<number | null>(
    wish?.goal_cents ?? null,
  );
  const [resetKey, setResetKey] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);
  const set = (p: Partial<typeof f>) => setF((o) => ({ ...o, ...p }));
  const fund = kind === "fund";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!f.name.trim())
      return setError(fund ? "Name the fund." : "Say what you'd like.");
    if (fund && !goal) return setError("Set a goal for the fund.");
    if (f.url.trim() && !/^https?:\/\//i.test(f.url.trim()))
      return setError("Links must start with http:// or https://");
    setError(null);
    try {
      await onSave({
        ...(!wish && { kind }),
        name: f.name.trim(),
        url: f.url.trim() || null,
        notes: f.notes.trim() || null,
        ...(fund
          ? { goal_cents: goal }
          : {
              price_cents: price,
              qty: Math.min(99, Math.max(1, Number(f.qty) || 1)),
            }),
      });
      if (!wish) {
        setF(blank);
        setPrice(null);
        setGoal(null);
        setResetKey((k) => k + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save.");
    }
  };

  return (
    <form
      onSubmit={submit}
      aria-label={wish ? `Edit ${wish.name}` : "Add a wish"}
      className="flex flex-col gap-3"
    >
      {!wish && (
        <div className="self-start">
          <Segmented
            label="Kind of wish"
            value={kind}
            onChange={setKind}
            options={[
              { value: "gift", label: "Gift", icon: Gift },
              { value: "fund", label: "Cash fund", icon: PiggyBank },
            ]}
          />
        </div>
      )}
      <div
        key={resetKey}
        className={
          fund
            ? "grid gap-2 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]"
            : "grid gap-2 sm:grid-cols-[minmax(0,2fr)_minmax(0,2fr)_minmax(0,1fr)_4.5rem]"
        }
      >
        <Input
          aria-label={fund ? "Fund name" : "Wish"}
          placeholder={
            fund ? "Honeymoon fund, college savings" : "What would you like?"
          }
          maxLength={200}
          value={f.name}
          onChange={(e) => set({ name: e.target.value })}
        />
        {!fund && (
          <Input
            type="url"
            aria-label="Link"
            placeholder="Shop link (optional)"
            maxLength={500}
            value={f.url}
            onChange={(e) => set({ url: e.target.value })}
          />
        )}
        {fund ? (
          <MoneyInput
            label="Goal"
            currency={currency}
            cents={goal}
            onChange={setGoal}
            placeholder="Goal"
          />
        ) : (
          <>
            <MoneyInput
              label="Price"
              currency={currency}
              cents={price}
              onChange={setPrice}
              placeholder={f.url.trim() ? "From the shop" : "Price"}
            />
            <Input
              type="number"
              aria-label="How many"
              min={1}
              max={99}
              value={f.qty}
              onChange={(e) => set({ qty: e.target.value })}
            />
          </>
        )}
      </div>
      <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
        <Input
          aria-label="Notes"
          placeholder={fund ? "What it's for" : "Size, color, details"}
          maxLength={500}
          value={f.notes}
          onChange={(e) => set({ notes: e.target.value })}
        />
        <div className="flex justify-end gap-2">
          {onCancel && (
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" loading={pending}>
            {wish ? "Save" : fund ? "Add fund" : "Add wish"}
          </Button>
        </div>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </form>
  );
}
