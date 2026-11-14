"use client";
/**
 * @file components/ui/Tooltip.tsx
 * @brief Radix tooltip wrapper. Mount TooltipProvider once (Shell); a
 *        Tooltip rendered outside any provider supplies its own fallback.
 */
import {
  createContext,
  useContext,
  type ComponentProps,
  type ReactElement,
  type ReactNode,
} from "react";
import {
  TooltipProvider as RProvider,
  Tooltip as RTooltip,
  TooltipContent,
  TooltipTrigger,
} from "./shadcn/tooltip";

/** Hover delay before a tooltip opens (ms). Focus opens immediately. */
export const TOOLTIP_DELAY_MS = 400;

const ProviderPresent = createContext(false);

/**
 * @brief App tooltip provider with a 400ms hover delay and skip-delay grouping.
 * @param props Radix provider props (delayDuration overridable)
 * @return provider element
 */
export function TooltipProvider({
  delayDuration = TOOLTIP_DELAY_MS,
  children,
  ...props
}: ComponentProps<typeof RProvider>) {
  return (
    <RProvider delayDuration={delayDuration} {...props}>
      <ProviderPresent.Provider value>{children}</ProviderPresent.Provider>
    </RProvider>
  );
}

export interface TooltipProps {
  content: ReactNode;
  children: ReactElement;
  side?: "top" | "right" | "bottom" | "left";
}

/**
 * @brief Tooltip shown on hover (after delay) and keyboard focus of the child.
 * @param props see TooltipProps
 * @return tooltip element
 */
export function Tooltip({ content, children, side = "top" }: TooltipProps) {
  const hasProvider = useContext(ProviderPresent);
  const tip = (
    <RTooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side}>{content}</TooltipContent>
    </RTooltip>
  );
  return hasProvider ? tip : <TooltipProvider>{tip}</TooltipProvider>;
}

export default Tooltip;
