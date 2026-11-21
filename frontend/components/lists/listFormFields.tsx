"use client";
/**
 * @file components/lists/listFormFields.tsx
 * @brief Shared form controls for list forms: color input.
 */
import * as React from "react";
import { Field, type FieldProps } from "@/components/ui/Field";

export const LIST_COLORS = [
  "#3366ff",
  "#16a34a",
  "#f59e0b",
  "#dc2626",
  "#9333ea",
  "#0891b2",
] as const;

/**
 * @brief Labelled color input (glass circle) with preset swatches via datalist.
 * @return color input
 */
export const ColorInput = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement> & FieldProps
>(function ColorInput({ label, error, hint, ...rest }, ref) {
  const listId = React.useId();
  return (
    <Field label={label} error={error} hint={hint}>
      {(a) => (
        <>
          <input
            ref={ref}
            type="color"
            list={listId}
            className="glass-item size-10 cursor-pointer appearance-none overflow-hidden rounded-full border-0 p-1 [&::-webkit-color-swatch-wrapper]:p-0 [&::-webkit-color-swatch]:rounded-full [&::-webkit-color-swatch]:border-0 [&::-moz-color-swatch]:rounded-full [&::-moz-color-swatch]:border-0"
            {...a}
            {...rest}
          />
          <datalist id={listId}>
            {LIST_COLORS.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </>
      )}
    </Field>
  );
});
