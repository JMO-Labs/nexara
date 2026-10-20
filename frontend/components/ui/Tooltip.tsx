"use client";
/**
 * @file components/ui/Tooltip.tsx
 * @brief Radix tooltip wrapper. Mount TooltipProvider once in Shell.
 */
import type { ReactElement, ReactNode } from "react";
import {
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
    <RTooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side}>{content}</TooltipContent>
    </RTooltip>
  );
}

export default Tooltip;
