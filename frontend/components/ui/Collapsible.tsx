"use client";
/**
 * @file components/ui/Collapsible.tsx
 * @brief Controlled collapsible section on Radix Collapsible.
 */
import * as React from "react";
import { Collapsible as C } from "radix-ui";

export interface CollapsibleProps {
  /** Controlled open state. */
  open: boolean;
  onOpenChange?: (open: boolean) => void;
  /** Header slot rendered inside the toggle button. */
  header: React.ReactNode;
  children: React.ReactNode;
  headerProps?: { "aria-label"?: string };
}

/**
 * @brief Toggleable section.
 * @param open controlled state
 * @param onOpenChange change callback
 * @param header toggle content
 * @return collapsible root
 */
export function Collapsible({
  open,
  onOpenChange,
  header,
  children,
  headerProps,
}: CollapsibleProps) {
  return (
    <C.Root open={open} onOpenChange={onOpenChange}>
      <C.Trigger
        aria-label={headerProps?.["aria-label"]}
        className="flex w-full items-center justify-between rounded text-left"
      >
        {header}
      </C.Trigger>
      <C.Content>{children}</C.Content>
    </C.Root>
  );
}

export default Collapsible;
