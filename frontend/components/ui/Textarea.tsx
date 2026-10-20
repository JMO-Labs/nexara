"use client";
/**
 * @file components/ui/Textarea.tsx
 * @brief Labelled textarea with error and hint.
 */
import * as React from "react";
import { Field, controlClass, type FieldProps } from "./Field";
import { cn } from "@/lib/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> &
  FieldProps;

/**
 * @brief Textarea primitive.
 * @param props native textarea props plus label, error, hint
 * @return labelled textarea
 */
export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea({ label, error, hint, className, id, ...rest }, ref) {
    return (
      <Field label={label} error={error} hint={hint} id={id}>
        {(a) => (
          <textarea
            ref={ref}
            className={cn(controlClass, "min-h-20 py-2", className)}
            {...a}
            {...rest}
          />
        )}
      </Field>
    );
  },
);

export default Textarea;
