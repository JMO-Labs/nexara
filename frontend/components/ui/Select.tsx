"use client";
/**
 * @file components/ui/Select.tsx
 * @brief Re-export Joy Select + Option with editorial defaults.
 */
import JoySelect, { type SelectProps as JoySelectProps } from "@mui/joy/Select";
import Option from "@mui/joy/Option";

export const Select = JoySelect;
export { Option };
export type SelectProps<T extends NonNullable<unknown> = NonNullable<unknown>> =
  JoySelectProps<T, false>;
export default Select;
