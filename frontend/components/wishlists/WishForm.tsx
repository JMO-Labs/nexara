"use client";
/**
 * @file components/wishlists/WishForm.tsx
 * @brief Add or edit one wish: name, link, price, how many, notes.
 */
import * as React from "react";
import { Button, Input } from "@/components/ui";
import type { Wish, WishInput } from "@/lib/api/wishlists";

/**
 * @brief Wish fields.
 * @param wish existing wish to edit, or undefined to add
 * @param pending saving
 * @param onSave called with the cleaned body; resolve to reset the form
 * @param onCancel optional cancel (edit mode)
 * @return form
 */
export function WishForm({
  wish,
  pending,
  onSave,
  onCancel,
}: {
  wish?: Wish;
  pending: boolean;
  onSave: (body: WishInput) => Promise<unknown>;
  onCancel?: () => void;
}) {
  const blank = { name: "", url: "", price: "", qty: "1", notes: "" };
  const [f, setF] = React.useState(
    wish
      ? {
          name: wish.name,
          url: wish.url ?? "",
          price: wish.price ?? "",
          qty: String(wish.qty),
          notes: wish.notes ?? "",
        }
      : blank,
  );
  const [error, setError] = React.useState<string | null>(null);
  const set = (p: Partial<typeof f>) => setF((o) => ({ ...o, ...p }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!f.name.trim()) return setError("Say what you'd like.");
    if (f.url.trim() && !/^https?:\/\//i.test(f.url.trim()))
      return setError("Links must start with http:// or https://");
    setError(null);
    try {
      await onSave({
        name: f.name.trim(),
        url: f.url.trim() || null,
        price: f.price.trim() || null,
        notes: f.notes.trim() || null,
        qty: Math.min(99, Math.max(1, Number(f.qty) || 1)),
      });
      if (!wish) setF(blank);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save.");
    }
  };

  return (
    <form
      onSubmit={submit}
      aria-label={wish ? `Edit ${wish.name}` : "Add a wish"}
      className="grid gap-2 sm:grid-cols-[minmax(0,2fr)_minmax(0,2fr)_minmax(0,1fr)_4.5rem]"
    >
      <Input
        aria-label="Wish"
        placeholder="What would you like?"
        maxLength={200}
        value={f.name}
        onChange={(e) => set({ name: e.target.value })}
      />
      <Input
        type="url"
        aria-label="Link"
        placeholder="Link (optional)"
        maxLength={500}
        value={f.url}
        onChange={(e) => set({ url: e.target.value })}
      />
      <Input
        aria-label="Price"
        placeholder="Price"
        maxLength={30}
        value={f.price}
        onChange={(e) => set({ price: e.target.value })}
      />
      <Input
        type="number"
        aria-label="How many"
        min={1}
        max={99}
        value={f.qty}
        onChange={(e) => set({ qty: e.target.value })}
      />
      <div className="sm:col-span-4 flex flex-col gap-2 sm:flex-row">
        <Input
          aria-label="Notes"
          placeholder="Size, color, details"
          maxLength={500}
          value={f.notes}
          onChange={(e) => set({ notes: e.target.value })}
          className="flex-1"
        />
        <div className="flex gap-2">
          {onCancel && (
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" loading={pending}>
            {wish ? "Save" : "Add wish"}
          </Button>
        </div>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive sm:col-span-4">
          {error}
        </p>
      )}
    </form>
  );
}
