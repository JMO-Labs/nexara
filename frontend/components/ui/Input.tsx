"use client";
/**
 * @file components/ui/Input.tsx
 * @brief Labelled text input with error and hint.
 */
import * as React from "react";
import { Field, controlClass, type FieldProps } from "./Field";
import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement> & FieldProps;

/**
 * @brief Input primitive.
 * @param props native input props plus label, error, hint
 * @return labelled input
 */
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  function Input({ label, error, hint, className, id, ...rest }, ref) {
    return (
      <Field label={label} error={error} hint={hint} id={id}>
        {(a) => (
          <input
            ref={ref}
            className={cn(controlClass, "h-10", className)}
            {...a}
            {...rest}
          />
        )}
      </Field>
    );
  },
);

export default Input;
