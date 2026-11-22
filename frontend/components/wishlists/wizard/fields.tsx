/**
 * @file components/wishlists/wizard/fields.tsx
 * @brief Small form pieces shared by the wishlist wizard steps.
 */
import * as React from "react";
import { Input } from "@/components/ui";
import { centsToInput, parseMoney } from "@/lib/money";

/** @brief Labelled field. */
export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={`flex flex-col gap-1 text-sm ${className ?? ""}`}>
      <span className="font-medium">{label}</span>
      {children}
      {hint && <span className="text-xs text-muted">{hint}</span>}
    </label>
  );
}

/** @brief Money input bound to integer cents. */
export function MoneyInput({
  cents,
  onChange,
  currency,
  label,
  placeholder,
}: {
  cents: number | null;
  onChange: (c: number | null) => void;
  currency: string;
  label: string;
  placeholder?: string;
}) {
  const [text, setText] = React.useState(centsToInput(cents));
  return (
    <span className="relative flex items-center">
      <Input
        aria-label={label}
        inputMode="decimal"
        placeholder={placeholder ?? "0"}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          onChange(parseMoney(e.target.value));
        }}
        className="pr-14"
      />
      <span
        aria-hidden
        className="pointer-events-none absolute right-4 text-xs text-muted"
      >
        {currency}
      </span>
    </span>
  );
}

export const selectCls =
  "glass-item h-10 rounded-full px-3 text-sm focus-visible:outline-2 focus-visible:outline-accent";
