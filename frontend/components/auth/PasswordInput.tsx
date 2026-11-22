"use client";
/**
 * @file components/auth/PasswordInput.tsx
 * @brief Password field with a show/hide toggle.
 */
import * as React from "react";
import { Eye, EyeOff } from "lucide-react";
import { Field, controlClass, type FieldProps } from "@/components/ui/Field";
import { cn } from "@/lib/utils";

type Props = Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> &
  FieldProps;

/** @brief Labelled password input; the eye button reveals what was typed. */
export const PasswordInput = React.forwardRef<HTMLInputElement, Props>(
  function PasswordInput({ label, error, hint, className, id, ...rest }, ref) {
    const [shown, setShown] = React.useState(false);
    return (
      <Field label={label} error={error} hint={hint} id={id}>
        {(a) => (
          <span className="relative block">
            <input
              ref={ref}
              type={shown ? "text" : "password"}
              className={cn(controlClass, "h-11 rounded-full pr-12", className)}
              {...a}
              {...rest}
            />
            <button
              type="button"
              onClick={() => setShown((v) => !v)}
              aria-label={shown ? "Hide password" : "Show password"}
              aria-pressed={shown}
              className="absolute inset-y-0 right-1 flex w-10 items-center justify-center rounded-full text-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
            >
              {shown ? (
                <EyeOff className="size-4" aria-hidden />
              ) : (
                <Eye className="size-4" aria-hidden />
              )}
            </button>
          </span>
        )}
      </Field>
    );
  },
);
