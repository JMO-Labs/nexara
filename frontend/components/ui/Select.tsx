"use client";
/**
 * @file components/ui/Select.tsx
 * @brief Radix Select wrapper with a simple value/children API.
 */
import * as React from "react";
import {
  Select as Root,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./select";

export interface SelectProps {
  value?: string;
  defaultValue?: string;
  onValueChange?: (v: string) => void;
  placeholder?: string;
  label?: string;
  disabled?: boolean;
  children: React.ReactNode;
}

/**
 * @brief Select primitive.
 * @param props select props; children are Option elements
 * @return select
 */
export function Select({ label, placeholder, children, ...root }: SelectProps) {
  return (
    <Root {...root}>
      <SelectTrigger aria-label={label} className="w-full">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>{children}</SelectContent>
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
