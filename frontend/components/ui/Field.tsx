"use client";
/**
 * @file components/ui/Field.tsx
 * @brief Shared label/hint/error wrapper for Input and Textarea.
 */
import * as React from "react";

export interface FieldProps {
  label?: string;
  error?: string;
  hint?: string;
}

/**
 * @brief Wire label + described-by ids around a control.
 * @param p field props and a render function receiving control attrs
 * @return labelled field
 */
export function Field({
  label,
  error,
  hint,
  id,
  children,
}: FieldProps & {
  id?: string;
  children: (a: {
    id: string;
    "aria-invalid"?: true;
    "aria-describedby"?: string;
  }) => React.ReactNode;
}) {
  const gen = React.useId();
  const cid = id ?? gen;
  const msgId = `${cid}-msg`;
  const msg = error ?? hint;
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={cid} className="text-sm font-medium">
          {label}
        </label>
      )}
      {children({
        id: cid,
        "aria-invalid": error ? true : undefined,
        "aria-describedby": msg ? msgId : undefined,
      })}
      {msg && (
        <p
          id={msgId}
          className={error ? "text-sm text-destructive" : "text-sm text-muted"}
        >
          {msg}
        </p>
      )}
    </div>
  );
}

export const controlClass =
  "glass-item w-full rounded-[20px] px-4 text-base text-ink placeholder:text-muted outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent aria-invalid:ring-1 aria-invalid:ring-[var(--nx-red)] disabled:opacity-50";
