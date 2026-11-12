"use client";
/**
 * @file components/ui/Tooltip.tsx
 * @brief Radix tooltip wrapper; self-provides TooltipProvider so it works standalone.
 */
import type { ReactElement, ReactNode } from "react";
import {
  TooltipProvider,
  Tooltip as RTooltip,
  TooltipContent,
  TooltipTrigger,
} from "./shadcn/tooltip";

export { TooltipProvider } from "./shadcn/tooltip";

export interface TooltipProps {
  content: ReactNode;
  children: ReactElement;
  side?: "top" | "right" | "bottom" | "left";
}

/**
 * @brief Tooltip shown on hover and keyboard focus of the child.
 * @param props see TooltipProps
 * @return tooltip element
 */
export function Tooltip({ content, children, side = "top" }: TooltipProps) {
  return (
    <TooltipProvider>
      <RTooltip>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent side={side}>{content}</TooltipContent>
      </RTooltip>
    </TooltipProvider>
  );
}

export default Tooltip;
