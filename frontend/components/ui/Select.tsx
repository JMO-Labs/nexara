"use client";
/**
 * @file components/ui/Select.tsx
 * @brief Radix Select wrapper with a simple value/children API.
 */
import * as React from "react";
import { cn } from "@/lib/utils";
import {
  Select as Root,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./shadcn/select";

export interface SelectProps {
  value?: string;
  defaultValue?: string;
  onValueChange?: (v: string) => void;
  placeholder?: string;
  label?: string;
  disabled?: boolean;
  /** Extra classes for the trigger (e.g. glass pill styling). */
  className?: string;
  children: React.ReactNode;
}

/** Trigger styled as the glass input pill (see controlClass in Field). */
const TRIGGER =
  "data-[size=default]:h-11 rounded-full border border-[color-mix(in_srgb,var(--nx-ink)_14%,transparent)] bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)] dark:bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)] dark:hover:bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)] px-4 shadow-none";

/**
 * @brief Select primitive.
 * @param props select props; children are Option elements
 * @return select
 */
export function Select({
  label,
  placeholder,
  className,
  children,
  ...root
}: SelectProps) {
  return (
    <Root {...root}>
      <SelectTrigger
        aria-label={label}
        className={cn(TRIGGER, "w-full", className)}
      >
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent className="glass rounded-[20px] border-0 bg-[var(--nx-glass-solid)] text-ink">
        {children}
      </SelectContent>
    </Root>
  );
}

/**
 * @brief Option within a Select.
 * @param props value and label children
 * @return select item
 */
export function Option(props: { value: string; children: React.ReactNode }) {
  return <SelectItem {...props} />;
}

export default Select;
