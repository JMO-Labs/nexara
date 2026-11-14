"use client";
/**
 * @file components/lists/listFormFields.tsx
 * @brief Shared form controls for list modals: native select and color input.
 */
import * as React from "react";
import { Field, controlClass, type FieldProps } from "@/components/ui/Field";
import { cn } from "@/lib/utils";

export const LIST_COLORS = [
  "#3366ff",
  "#16a34a",
  "#f59e0b",
  "#dc2626",
  "#9333ea",
  "#0891b2",
] as const;

/**
 * @brief Labelled native select (testable, keyboard friendly).
 * @return select element
 */
export const NativeSelect = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement> & FieldProps
>(function NativeSelect({ label, error, hint, className, ...rest }, ref) {
  return (
    <Field label={label} error={error} hint={hint}>
      {(a) => (
        <select
          ref={ref}
          className={cn(controlClass, "h-10", className)}
          {...a}
          {...rest}
        />
      )}
    </Field>
  );
});

/**
 * @brief Labelled color input with preset swatches via datalist.
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
            className="h-10 w-16 cursor-pointer rounded-xl border border-current/30 bg-surface p-1"
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
